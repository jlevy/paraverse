import Foundation

struct InterestSuggestion: Codable, Identifiable, Equatable, Sendable {
    var label: String
    var reason: String
    var sourceURL: URL?
    var category: String?
    var confidence: String?
    var evidence: [ProfileEvidence]?
    var id: String { label.lowercased() }
}
struct ProfileEvidence: Codable, Equatable, Sendable {
    var sourceURL: URL
    var quote: String
    var date: String?
}
struct ImportJob: Codable {
    var jobID: String?
    var status: String?
    var profile: ImportedProfile?
    var error: String?
}
struct ImportedProfile: Codable, Sendable {
    var avatarURL: String?
    var background: String
    var title: String?
    var provenance: String?
    var interests: [InterestSuggestion]
}
protocol ProfileImporting: Sendable {
    func read(linkedIn: String?, x: String?, github: String?) async throws -> ImportedProfile
}

enum ProfileEnrichment {
    /// Return a complete replacement only after the request succeeds; callers keep their draft on failure.
    static func refresh(_ original: AttendeeProfile, using importer: any ProfileImporting) async throws -> AttendeeProfile {
        let result = try await importer.read(linkedIn: original.linkedInURL, x: original.xURL, github: original.githubURL)
        try Task.checkCancellation()
        guard !result.background.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || !result.interests.isEmpty else {
            throw ProfileImportError.invalidResponse
        }
        var updated = original
        if !result.background.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { updated.background = result.background }
        if let title = result.title, !title.isEmpty { updated.title = title }
        if let avatar = result.avatarURL { updated.avatarURL = avatar }
        if !result.interests.isEmpty {
            var seen = Set<String>()
            let suggestions = result.interests.filter { seen.insert($0.id).inserted }
            updated.interestSuggestions = suggestions
            updated.personalInterests = (original.personalInterests ?? []).union(suggestions.filter { $0.category == "personal" }.map(\.label))
            for item in suggestions { InterestSelection.add(item.label, to: &updated.interests) }
        }
        return updated
    }
}
enum ProfileImportError: LocalizedError {
    case unavailable, failed, invalidResponse
    var errorDescription: String? {
        switch self {
        case .unavailable: "Profile import isn’t available yet. Choose your interests below to continue."
        case .failed: "We couldn’t read those profiles. You can choose your interests and try again later."
        case .invalidResponse: "We couldn’t use the profile results. Choose your interests below."
        }
    }
}
// Bright Data and model credentials belong on the backend, never in the app.
struct ProfileImportClient: ProfileImporting {
    var endpoint: URL? = URL(string: ProcessInfo.processInfo.environment["COMMON_GROUND_PROFILE_ENDPOINT"] ?? "http://127.0.0.1:8765/profiles")
    func read(linkedIn: String?, x: String?, github: String? = nil) async throws -> ImportedProfile {
        guard let endpoint else { throw ProfileImportError.unavailable }
        guard endpoint.scheme == "https" || (endpoint.scheme == "http" && ["localhost", "127.0.0.1"].contains(endpoint.host ?? "")) else { throw ProfileImportError.unavailable }
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.timeoutInterval = 35
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: ["linkedin_url": linkedIn ?? "", "x_url": x ?? "", "github_url": github ?? ""])
        var (data, response) = try await URLSession.shared.data(for: request)
        if (response as? HTTPURLResponse)?.statusCode == 202 {
            let start = try JSONDecoder().decode(ImportJob.self, from: data)
            guard let id = start.jobID, id.count == 32, id.allSatisfy({ $0.isHexDigit }) else { throw ProfileImportError.invalidResponse }
            let statusURL = endpoint.appendingPathComponent(id)
            for _ in 0..<360 {
                try await Task.sleep(for: .seconds(3))
                try Task.checkCancellation()
                (data, response) = try await URLSession.shared.data(from: statusURL)
                guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw ProfileImportError.failed }
                let job = try JSONDecoder().decode(ImportJob.self, from: data)
                if job.status == "failed" { throw ProfileImportError.failed }
                if job.status == "ready", let profile = job.profile {
                    data = try JSONEncoder().encode(profile)
                    break
                }
            }
        }
        guard let response = response as? HTTPURLResponse, response.statusCode == 200 else { throw ProfileImportError.failed }
        guard data.count < 200_000, let profile = try? JSONDecoder().decode(ImportedProfile.self, from: data), profile.background.count <= 3000, profile.interests.count <= 30,
              profile.interests.allSatisfy({ !$0.label.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && $0.label.count <= 60 && !$0.reason.isEmpty }) else { throw ProfileImportError.invalidResponse }
        return profile
    }
}

enum InterestSelection {
    static func add(_ value: String, to selected: inout Set<String>) {
        let clean = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !clean.isEmpty, clean.count <= 60, !selected.contains(where: { $0.caseInsensitiveCompare(clean) == .orderedSame }) else { return }
        selected.insert(clean)
    }
}
