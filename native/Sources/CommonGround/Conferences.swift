import SwiftUI

enum ConferenceStatus: String, Codable, CaseIterable {
    case none = "Not saved", interested = "Interested", going = "Planning to go"
}
struct ConferenceRecord: Identifiable, Codable, Sendable {
    let id, title, start, end, dates, city, venue, price, url: String
    let online: Bool
    let themes: [String]
    let program: String
    var imageURL: URL?
}
struct ConferenceSource: Codable, Sendable {
    let url: URL
    let title: String
    let quotes: [String]
}
struct ConferenceMatch: Identifiable, Codable, Sendable {
    let conference: ConferenceRecord
    let matchedInterests: [String]
    let locationNote: String
    let reason: String
    let sources: [ConferenceSource]
    var id: String { conference.id }
    var title: String { conference.title }
}

extension ConferenceMatch {
    static let featuredUniverse = ConferenceMatch(
        conference: ConferenceRecord(id: "universe-2026", title: "GitHub Universe 2026", start: "2026-10-28", end: "2026-10-29", dates: "Oct 28–29, 2026", city: "San Francisco", venue: "Fort Mason Center", price: "In-person tickets sold out · Free virtual attendance", url: "https://githubuniverse.com/", online: true, themes: ["Developer tools", "AI", "Software engineering"], program: "Developer tools, AI, and software engineering. Explore the published sessions and build your schedule.", imageURL: URL(string: "https://githubuniverse.com/og-image-26-2.png")),
        matchedInterests: [], locationNote: "Featured conference", reason: "Featured conference. Explore its published developer sessions, attendees, and schedule.",
        sources: [ConferenceSource(url: URL(string: "https://githubuniverse.com/")!, title: "GitHub Universe", quotes: [])])
}

struct ConferenceResults: Codable, Sendable {
    let matches: [ConferenceMatch]
    let generatedAt: String
    let searchedCount, verifiedCount: Int
    let summary: String
}
struct ConferenceJob: Decodable {
    let jobID: String?
    let status: String?
    let result: ConferenceResults?
    let error: String?
}
struct ConferenceQuery: Encodable {
    let title, background, city, travel: String
    let interests: [String]
    init(_ profile: AttendeeProfile) {
        title = profile.title ?? ""; background = profile.background
        city = profile.city; travel = profile.travel; interests = profile.interests.sorted()
    }
    var data: Data { (try? JSONEncoder().encode(self)) ?? Data() }
    var identity: String { [title, background, city, travel, interests.joined(separator: "\u{001F}")].joined(separator: "\u{001E}") }
}
enum ConferenceError: LocalizedError {
    case service(String)
    var errorDescription: String? { switch self { case .service(let message): return message } }
}
@MainActor enum ConferenceMemory {
    struct Entry: Codable { let savedAt: Date; let result: ConferenceResults }
    static var results: [String: Entry] = [:]
    static func cached(_ query: ConferenceQuery) -> ConferenceResults? {
        let key = LocalCache.key("six-recommendations-v2:" + query.identity)
        let entry = results[key] ?? (try? Data(contentsOf: LocalCache.directory.appendingPathComponent(key + ".json"))).flatMap { try? JSONDecoder().decode(Entry.self, from: $0) }
        guard let entry, Date().timeIntervalSince(entry.savedAt) < 21600 else { return nil }
        results[key] = entry
        return entry.result
    }
    static func save(_ result: ConferenceResults, for query: ConferenceQuery) {
        let key = LocalCache.key("six-recommendations-v2:" + query.identity), entry = Entry(savedAt: Date(), result: result)
        results[key] = entry
        if let data = try? JSONEncoder().encode(entry) { try? data.write(to: LocalCache.directory.appendingPathComponent(key + ".json"), options: .atomic) }
    }
}
struct ConferenceClient {
    @MainActor func search(_ query: ConferenceQuery, progress: @escaping @MainActor (String) -> Void) async throws -> ConferenceResults {
        if let cached = ConferenceMemory.cached(query) { return cached }
        let result = try await fetch(query, progress: progress)
        ConferenceMemory.save(result, for: query)
        return result
    }
    private func fetch(_ query: ConferenceQuery, progress: @escaping @MainActor (String) -> Void) async throws -> ConferenceResults {
        let endpoint = URL(string: "http://127.0.0.1:8765/conferences")!
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"; request.timeoutInterval = 30
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = query.data
        let (data, response) = try await URLSession.shared.data(for: request)
        let status = (response as? HTTPURLResponse)?.statusCode
        if status == 200 { return try JSONDecoder().decode(ConferenceResults.self, from: data) }
        let job = try JSONDecoder().decode(ConferenceJob.self, from: data)
        guard status == 202, let id = job.jobID, id.count == 64, id.allSatisfy({ $0.isHexDigit }) else {
            throw ConferenceError.service(job.error ?? "Couldn’t start conference research. Please retry.")
        }
        for _ in 0..<200 {
            try await Task.sleep(for: .seconds(3))
            try Task.checkCancellation()
            let (next, response) = try await URLSession.shared.data(from: endpoint.appendingPathComponent(id))
            guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw ConferenceError.service("Couldn’t check your conference search.") }
            let job = try JSONDecoder().decode(ConferenceJob.self, from: next)
            if job.status == "failed" { throw ConferenceError.service(job.error ?? "Conference research failed. Please retry.") }
            if let result = job.result, job.status == "ready" { return result }
            await progress(job.status == "ranking" ? "Finding your strongest matches…" : job.status == "verifying" ? "Checking dates and conference details…" : "Discovering upcoming conferences…")
        }
        throw ConferenceError.service("Research is taking longer than expected. Try again to reconnect.")
    }
}
extension AttendeeProfile {
    func status(for id: String) -> ConferenceStatus { conferenceStates?[id] ?? .none }
    mutating func setStatus(_ status: ConferenceStatus, for event: ConferenceRecord) {
        if conferenceStates == nil { conferenceStates = [:] }
        conferenceStates?[event.id] = status
        if status == .none { conferences.remove(event.title); groupMatchingIDs?.remove(event.id) }
        else { conferences.insert(event.title) }
    }
}
struct ConferenceCards: View {
    @Binding var profile: AttendeeProfile
    var openConference: (() -> Void)? = nil
    @State private var results: ConferenceResults?
    @State private var loading = true
    @State private var progress = "Discovering upcoming conferences…"
    @State private var error: String?
    @State private var retry = 0
    init(profile: Binding<AttendeeProfile>, openConference: (() -> Void)? = nil) {
        _profile = profile; self.openConference = openConference
        let cached = ConferenceMemory.cached(ConferenceQuery(profile.wrappedValue))
        _results = State(initialValue: cached)
        _loading = State(initialValue: cached == nil)
    }
    var body: some View {
        VStack(alignment: .leading, spacing: GroundLayout.sectionGap) {
            if loading {
                HStack(spacing: 12) { ProgressView().controlSize(.small); Text(progress).foregroundStyle(.secondary) }.padding(.vertical, 24)
            }
            if let error {
                VStack(alignment: .leading, spacing: 10) {
                    Text(error).foregroundStyle(.secondary)
                    Button("Try again") { retry += 1 }
                }.padding(.vertical, 16)
            }
            let matches = [ConferenceMatch.featuredUniverse] + (results?.matches ?? []).filter { $0.id != "universe-2026" }
            if !loading && error == nil && matches.isEmpty {
                ContentUnavailableView("No matches yet", systemImage: "calendar.badge.magnifyingglass", description: Text("We couldn’t verify a strong match within the next six months. Update your interests to find more conferences."))
            }
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 260, maximum: 300), spacing: 16, alignment: .top)], alignment: .leading, spacing: 16) {
                ForEach(Array(matches.prefix(6))) { match in
                    DiscoveryCard(match: match, profile: $profile, openConference: openConference)
                }
            }
        }

        .task(id: ConferenceQuery(profile).identity + String(retry)) {
            let query = ConferenceQuery(profile)
            results = ConferenceMemory.cached(query); error = nil; loading = results == nil; progress = "Discovering upcoming conferences…"
            do {
                let found = try await ConferenceClient().search(query) { progress = $0 }
                try Task.checkCancellation()
                results = found; loading = false
            } catch {
                if !Task.isCancelled {
                    self.error = (error as? ConferenceError)?.localizedDescription ?? "Couldn’t reach conference research. Please check that the local service is running."
                    loading = false
                }
            }
        }
    }
}


private struct DiscoveryCard: View {
    let match: ConferenceMatch
    @Binding var profile: AttendeeProfile
    var openConference: (() -> Void)?
    private var event: ConferenceRecord { match.conference }
    private var status: ConferenceStatus { profile.status(for: event.id) }
    private var canEnter: Bool { event.id == "universe-2026" && openConference != nil }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top, spacing: 12) {
                ConferenceSprite(event: event)
                    .frame(width: 44, height: 44)
                    .accessibilityHidden(true)
                VStack(alignment: .leading, spacing: 6) {
                    Text(event.discoveryTitle)
                        .font(.system(size: 16, weight: .bold, design: .monospaced))
                        .foregroundStyle(Brand.welcomeTitle)
                        .lineLimit(3)
                        .help(event.title)
                    Text(event.dates)
                        .font(.system(size: 11))
                        .foregroundStyle(Brand.welcomeSubtitle)
                        .lineLimit(2)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            VStack(alignment: .leading, spacing: 6) {
                if profile.travel != "Nearby" || cityKey(event.city) != cityKey(profile.city) {
                    Text(event.city)
                        .font(.system(size: 12))
                        .foregroundStyle(Brand.welcomeSubtitle)
                }
                Text(event.discoverySummary)
                    .font(.system(size: 12))
                    .foregroundStyle(Brand.welcomeSubtitle)
                    .lineLimit(2, reservesSpace: true)
                    .help(event.discoverySummary)
            }
            Divider()
            HStack(spacing: 8) {
                interestButton
                Spacer(minLength: 12)
                Button { openConference?() } label: {
                        Label("Enter", systemImage: "arrow.right")
                            .font(.system(size: 12, weight: .semibold))
                            .padding(.horizontal, 10)
                            .frame(minHeight: GroundLayout.controlHeight)
                            .foregroundStyle(canEnter ? Brand.welcomeTitle : Color.secondary)
                            .background(PixelPanel().fill(canEnter ? Brand.primaryAction : Color.gray.opacity(0.12)))
                            .overlay(PixelPanel().stroke(canEnter ? Brand.buttonBorder : Color.gray.opacity(0.3), lineWidth: 1))
                }
                .buttonStyle(.plain)
                .disabled(!canEnter)
                .help(canEnter ? "Enter the GitHub Universe world" : "This conference world is not available yet")
                .accessibilityHint(canEnter ? "Opens the conference world" : "This conference world is not available yet")
            }.frame(height: GroundLayout.controlHeight)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(PixelPanel().fill(Brand.buttonSecondary.opacity(0.6)))
        .overlay(PixelPanel().stroke(Brand.fieldBorder.opacity(0.55), lineWidth: 1))
    }

    private func cityKey(_ value: String) -> String {
        value.split(separator: ",").first.map(String.init)?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() ?? ""
    }

    private var interestButton: some View {
        Button {
            profile.setStatus(status == .none ? .interested : .none, for: event)
        } label: {
            Label("Interested", systemImage: status == .none ? "star" : "star.fill")
                .font(.system(size: 12, weight: .medium))
                .padding(.horizontal, 6)
                .frame(minHeight: GroundLayout.controlHeight)
                .foregroundStyle(status == .none ? Brand.welcomeSubtitle : Brand.fieldFocus)
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(status == .none ? [] : .isSelected)
        .help(status == .going ? "Saved as going. Click to remove from your conferences." : status == .interested ? "Remove interest" : "Save as interested")
    }

}

/// Decorative topic sprites, not official conference logos.
private struct ConferenceSprite: View {
    let event: ConferenceRecord
    private static let panelCount = 5
    private static let sprites: [CGImage] = {
        guard let image = NSImage(contentsOf: worldAsset("WorldArt/ConferenceSprites.png")),
              let source = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return [] }
        let side = source.width / panelCount
        return (0..<panelCount).compactMap { index in
            source.cropping(to: CGRect(x: index * side, y: (source.height - side) / 2, width: side, height: side))
        }
    }()
    private var index: Int {
        let title = event.title.lowercased()
        if title.contains("universe") { return 0 }
        if title.contains("port") { return 1 }
        if title.contains("ruby") { return 2 }
        if title.contains("ux") || event.themes.contains(where: { $0.lowercased().contains("design") }) { return 3 }
        return 4
    }
    var body: some View {
        Group {
            if Self.sprites.indices.contains(index) {
                Image(decorative: Self.sprites[index], scale: 1)
                    .resizable().interpolation(.none).scaledToFit()
            } else { PixelPlanet() }
        }.accessibilityHidden(true)
    }
}
