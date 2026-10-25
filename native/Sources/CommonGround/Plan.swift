import Foundation
import SwiftUI

struct Message: Identifiable {
    let id = UUID()
    let text: String
    let isUser: Bool
    var hasPlan = false
    var recommendations: [PersonRecommendation] = []
    var eventDraft: LumaEventDraft?
    var eventSessions: [PlannedSession] = []
}
struct PlannedSession: Codable, Identifiable {
    let id, title, speakers, start, end, location, sourceURL, reason: String
    var registrationStatus: String?
    var priceStatus: String?
    var description: String?
    private static let catalogDescriptions: [String: String] =
        (try? JSONDecoder().decode([String: String].self, from: Data(contentsOf: worldAsset("session-descriptions.json")))) ?? [:]
    var about: String? { description ?? Self.catalogDescriptions[id] }
    var startDate: Date { ISO8601DateFormatter().date(from: start)! }
    var endDate: Date { ISO8601DateFormatter().date(from: end)! }
    var day: String { String(start.prefix(10)) }
    var time: String {
        let f = DateFormatter(); f.timeZone = TimeZone(identifier: "America/Los_Angeles"); f.dateFormat = "h:mm a"
        return f.string(from: startDate) + "–" + f.string(from: endDate)
    }
}
struct PersonRecommendation: Codable, Identifiable {
    let personID, name, role, reason, profileURL, sourceURL: String
    let avatarAsset: String?
    var linkedinURL: String?
    var xURL: String?
    var githubURL: String?
    var id: String { personID }
}
struct CompanionReply: Decodable {
    let action: String
    let message: String
    var recommendations: [PersonRecommendation]?
    var eventDraft: LumaEventDraft?
    var sessionIDs: [String]?
    private static let catalog: [PlannedSession] = {
        let groups = (try? JSONDecoder().decode([String: [PlannedSession]].self, from: Data(contentsOf: worldAsset("browse-events.json")))) ?? [:]
        return (groups["sessions"] ?? []) + (groups["external"] ?? [])
    }()
    func eventCards(catalog: [PlannedSession]? = nil) -> [PlannedSession] {
        let known = catalog ?? Self.catalog
        var seen = Set<String>()
        return (sessionIDs ?? []).compactMap { id in
            guard seen.insert(id).inserted,
                  let event = known.first(where: { $0.id == id }),
                  ISO8601DateFormatter().date(from: event.start) != nil,
                  ISO8601DateFormatter().date(from: event.end) != nil else { return nil }
            return event
        }
    }
}
struct SessionPlanResponse: Decodable { let sessions: [PlannedSession]; let message: String; let calendarChecked: Bool }
@MainActor @Observable final class Planner {
    var storage = UserDefaults.standard
    var messages: [Message] = []
    var sessions: [PlannedSession] = []
    var sideEvents: [PlannedSession] = []
    var peopleToMeet: [PersonRecommendation] = []
    var hasPlan = false
    var showPlan = false
    var late = false
    var busy = false
    var generatingRecommendations = false
    var recommendationWarnings: [String] = []
    var prompt = ""
    var status = "Ready to plan"
    var calendarChecked = false
    var savedToCalendar = false
    private var profile = AttendeeProfile()
    private var lastRankingRequest = "Recommend speaker sessions for both days"
    private var work: Task<Void, Never>?
    var requestData: (URLRequest) async throws -> (Data, URLResponse) = { try await URLSession.shared.data(for: $0) }
    private var generation = UUID()
    private static func fingerprint(_ profile: AttendeeProfile) -> String {
        func normalized(_ value: String?) -> String { (value ?? "").trimmingCharacters(in: .whitespacesAndNewlines) }
        let fields = [normalized(profile.name), normalized(profile.linkedInURL), normalized(profile.xURL), normalized(profile.githubURL), normalized(profile.title), normalized(profile.background)]
        let interests = Set(profile.interests.map { normalized($0) }.filter { !$0.isEmpty }).sorted()
        return String(data: try! JSONEncoder().encode([fields, interests]), encoding: .utf8)!
    }
    private var profileKey: String { Self.fingerprint(profile) }
    private func checkGeneration(_ captured: UUID) throws {
        try Task.checkCancellation()
        guard generation == captured else { throw CancellationError() }
    }
    func persistPlan() {
        let defaults = storage
        defaults.set(profileKey, forKey: "sessionPlanProfile")
        defaults.set(try? JSONEncoder().encode(sessions), forKey: "lastSessionPlan")
        defaults.set(try? JSONEncoder().encode(sideEvents), forKey: "lastSideEvents")
        defaults.set(try? JSONEncoder().encode(peopleToMeet), forKey: "lastPlanPeople")
        defaults.set(savedToCalendar, forKey: "sessionPlanSaved")
    }
    func generate(late newLate: Bool = false, request text: String = "Recommend speaker sessions for both days", external: Bool = false, completePlan: Bool = false) {
        guard !busy else { return }
        let earliestReveal = ContinuousClock.now.advanced(by: .seconds(5))
        generatingRecommendations = completePlan
        if completePlan { showPlan = false; recommendationWarnings = [] }
        busy = true; status = external ? "Finding events around your sessions…" : "Matching your interests to speaker sessions…"
        let timingOnly = ["i can only arrive after 3 pm", "arrive after 3 pm", "after 3 pm", "after 3", "after 15:00"].contains(text.lowercased().trimmingCharacters(in: .whitespacesAndNewlines.union(.punctuationCharacters)))
        let rankingText = timingOnly && !external ? lastRankingRequest : text
        let generation = self.generation
        let requestedProfile = profile
        work = Task {
            do {
                let connection = CalendarConnection.shared; connection.refresh()
                let start = ISO8601DateFormatter().date(from: "2026-10-26T00:00:00-07:00")!
                let end = ISO8601DateFormatter().date(from: "2026-10-30T00:00:00-07:00")!
                let formatter = ISO8601DateFormatter()
                var occupied = connection.events(from: start, to: end).filter { $0.availability != .free && !($0.notes ?? "").contains("Paraverse session:") && !($0.notes ?? "").contains("Common Ground session:") }.map { ["start": formatter.string(from: $0.startDate), "end": formatter.string(from: $0.endDate)] }
                if external { occupied += sessions.map { ["start": $0.start, "end": $0.end] } }
                let profileData = try JSONSerialization.jsonObject(with: JSONEncoder().encode(requestedProfile))
                let result: SessionPlanResponse = try await requestJSON("session-plan", body: ["profile": profileData, "prompt": rankingText, "late": newLate, "busy": occupied, "calendarConnected": connection.selected != nil, "external": external])
                guard result.sessions.allSatisfy({ ISO8601DateFormatter().date(from: $0.start) != nil && ISO8601DateFormatter().date(from: $0.end) != nil }) else { throw ProfileImportError.invalidResponse }
                try checkGeneration(generation)
                if external { sideEvents = result.sessions } else { sessions = result.sessions; savedToCalendar = false }; calendarChecked = result.calendarChecked; late = newLate
                if !external { lastRankingRequest = rankingText }
                var incompleteSections: [String] = []
                if completePlan {
                    status = "Finding people you’ll click with…"
                    do {
                        let reply: CompanionReply = try await requestJSON("chat", body: ["profile": profileData, "prompt": "Who should I meet at GitHub Universe based on my interests? Recommend at least 10 people, including both attendees and speakers, with a specific reason for each match.", "sessions": try JSONSerialization.jsonObject(with: JSONEncoder().encode(sessions)), "history": []])
                        try checkGeneration(generation)
                        peopleToMeet = reply.recommendations ?? []
                    } catch {
                        try checkGeneration(generation)
                        incompleteSections.append(peopleToMeet.isEmpty ? "People recommendations couldn’t load. Try again." : "People couldn’t refresh. Showing your saved recommendations.")
                    }
                    status = "Finding side quests around your sessions…"
                    do {
                        let events: SessionPlanResponse = try await requestJSON("session-plan", body: ["profile": profileData, "prompt": "Recommend up to 10 external events across the available days that fit my interests and do not overlap my conference sessions. Explain specifically why each fits me.", "late": newLate, "busy": occupied + sessions.map { ["start": $0.start, "end": $0.end] }, "calendarConnected": connection.selected != nil, "external": true])
                        guard events.sessions.allSatisfy({ ISO8601DateFormatter().date(from: $0.start) != nil && ISO8601DateFormatter().date(from: $0.end) != nil }) else { throw ProfileImportError.invalidResponse }
                        try checkGeneration(generation)
                        sideEvents = events.sessions
                    } catch {
                        try checkGeneration(generation)
                        incompleteSections.append(sideEvents.isEmpty ? "External events couldn’t load. Try again." : "External events couldn’t refresh. Showing your saved recommendations.")
                    }
                }
                try checkGeneration(generation)
                if completePlan {
                    try await ContinuousClock().sleep(until: earliestReveal)
                    try checkGeneration(generation)
                }
                if completePlan { recommendationWarnings = incompleteSections }
                else if external { recommendationWarnings.removeAll { $0.hasPrefix("External") || $0.hasPrefix("Side events") } }
                hasPlan = true; showPlan = true; status = incompleteSections.isEmpty ? "Plan ready" : "Plan ready with some missing recommendations"; persistPlan()
                if completePlan {
                    messages.append(Message(text: "Your plan is ready with \(sessions.count) sessions, \(peopleToMeet.count) people to meet, and \(sideEvents.count) side quests. " + incompleteSections.joined(separator: " "), isUser: false, hasPlan: true, recommendations: peopleToMeet))
                } else {

                messages.append(Message(text: (external ? "Here are optional events that fit around your sessions. Check registration before making plans." : result.message + " I can also suggest external events for after the conference.") + (calendarChecked ? " Scheduled around your selected calendar." : " Connect a calendar to check your availability.") + " Review the plan before saving.", isUser: false, hasPlan: true))
                }
            } catch { if generation == self.generation && !Task.isCancelled { status = "Couldn’t prepare your plan"; messages.append(Message(text: "I couldn’t load your session recommendations. Check the local service and try again.", isUser: false)) } }
            guard generation == self.generation else { return }
            generatingRecommendations = false
            busy = false
        }
    }
    private func requestJSON<Response: Decodable>(_ endpoint: String, body: [String: Any]) async throws -> Response {
        var request = URLRequest(url: URL(string: "http://127.0.0.1:8765/" + endpoint)!)
        request.httpMethod = "POST"
        request.timeoutInterval = 210
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        for attempt in 0..<3 {
            try Task.checkCancellation()
            do {
                let (data, response) = try await requestData(request)
                let status = (response as? HTTPURLResponse)?.statusCode ?? 0
                if status == 429 || (500...599).contains(status) {
                    guard attempt < 2 else { throw ProfileImportError.failed }
                } else {
                    guard status == 200 else { throw ProfileImportError.failed }
                    return try JSONDecoder().decode(Response.self, from: data)
                }
            } catch let error as URLError {
                let transient: [URLError.Code] = [.timedOut, .cannotConnectToHost, .networkConnectionLost, .notConnectedToInternet, .cannotFindHost]
                guard attempt < 2 && transient.contains(error.code) else { throw error }
            }
            try await Task.sleep(for: .milliseconds(attempt == 0 ? 250 : 750))
        }
        throw ProfileImportError.failed
    }

    func send(_ text: String? = nil) {
        let value = (text ?? prompt).trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty, !busy else { return }
        prompt = ""; messages.append(Message(text: value, isUser: true))
        if value.lowercased().contains("invite"),
           let draft = messages.compactMap(\.eventDraft).last {
            messages.append(Message(text: "Choose who to invite below. Linked demo recipients are selected for you.", isUser: false, eventDraft: draft))
            return
        }
        busy = true; status = "Thinking…"
        let generation = self.generation
        let requestedProfile = profile
        work = Task {
            do {
                var request = URLRequest(url: URL(string: "http://127.0.0.1:8765/chat")!)
                request.httpMethod = "POST"; request.timeoutInterval = 190
                request.setValue("application/json", forHTTPHeaderField: "Content-Type")
                let profileData = try JSONSerialization.jsonObject(with: JSONEncoder().encode(requestedProfile))
                let planData = try JSONSerialization.jsonObject(with: JSONEncoder().encode(sessions))
                request.httpBody = try JSONSerialization.data(withJSONObject: ["profile": profileData, "prompt": value, "sessions": planData, "history": messages.dropLast().suffix(8).map { ["role": $0.isUser ? "user" : "assistant", "text": $0.text] }])
                let (data, response) = try await URLSession.shared.data(for: request)
                guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw ProfileImportError.failed }
                let reply = try JSONDecoder().decode(CompanionReply.self, from: data)
                try checkGeneration(generation)
                busy = false; status = "Ready"
                switch reply.action {
                case "plan_sessions": generate(late: value.lowercased().contains("after 3") || value.contains("15:00"), request: value)
                case "side_events": generate(late: late, request: value, external: true)
                case "show_calendar": messages.append(Message(text: "Open Calendar in the sidebar to see your events.", isUser: false))
                default:
                    let cards = reply.eventCards()
                    messages.append(Message(text: reply.message, isUser: false, recommendations: reply.recommendations ?? [], eventDraft: reply.eventDraft, eventSessions: cards))
                }
            } catch {
                if generation == self.generation && !Task.isCancelled { busy = false; status = "Couldn’t answer"; messages.append(Message(text: "I couldn’t answer that question right now. Please try again.", isUser: false)) }
            }
        }
    }

    func refreshExternalEvents() {
        guard !busy else { return }
        busy = true; status = "Finding events across your conference week…"
        let generation = self.generation
        let requestedProfile = profile
        let requestedLate = late
        work = Task {
            defer { if generation == self.generation { busy = false } }
            do {
                let profileData = try JSONSerialization.jsonObject(with: JSONEncoder().encode(requestedProfile))
                let occupied = sessions.map { ["start": $0.start, "end": $0.end] }
                let reply: SessionPlanResponse = try await requestJSON("session-plan", body: ["profile": profileData, "prompt": "Recommend up to 10 external events across the available days that fit my interests and do not overlap my conference sessions. Explain specifically why each fits me.", "busy": occupied, "late": requestedLate, "external": true])
                try checkGeneration(generation)
                sideEvents = reply.sessions
                recommendationWarnings.removeAll { $0.hasPrefix("External") || $0.hasPrefix("Side events") }
                persistPlan(); status = "External events ready"
            } catch { if generation == self.generation && !Task.isCancelled { status = "Couldn’t refresh external events. Please try again." } }
        }
    }

    func refreshPeople() {
        guard !busy else { return }
        busy = true; status = "Finding people who share your interests…"
        let generation = self.generation
        let requestedProfile = profile
        work = Task {
            defer { if generation == self.generation { busy = false } }
            do {
                let profileData = try JSONSerialization.jsonObject(with: JSONEncoder().encode(requestedProfile))
                let reply: CompanionReply = try await requestJSON("chat", body: ["profile": profileData, "prompt": "Who should I meet at GitHub Universe based on my interests? Recommend at least 10 people, including both attendees and speakers, with a specific reason for each match.", "sessions": try JSONSerialization.jsonObject(with: JSONEncoder().encode(sessions)), "history": []])
                try checkGeneration(generation)
                guard let people = reply.recommendations, people.count >= 10 else { throw ProfileImportError.failed }
                peopleToMeet = people
                recommendationWarnings.removeAll { $0.hasPrefix("People") }
                persistPlan()
                status = "People recommendations ready"
            } catch {
                guard generation == self.generation && !Task.isCancelled else { return }
                status = "Couldn’t refresh people. Please try again."
                messages.append(Message(text: status, isUser: false))
            }
        }
    }

    func start(for profile: AttendeeProfile) {
        reset(); self.profile = profile
        SessionWarmup.prepare(profile)
        messages = [Message(text: "I’ll use your profile to recommend speaker sessions for October 28 and 29. You can ask for a topic or a later start.", isUser: false)]
        let defaults = storage
        if defaults.string(forKey: "sessionPlanProfile") == profileKey, let data = defaults.data(forKey: "lastSessionPlan"), let saved = try? JSONDecoder().decode([PlannedSession].self, from: data) {
            sessions = saved; hasPlan = !saved.isEmpty; savedToCalendar = defaults.bool(forKey: "sessionPlanSaved")
            if let sideData = defaults.data(forKey: "lastSideEvents") { sideEvents = (try? JSONDecoder().decode([PlannedSession].self, from: sideData)) ?? [] }
            if let peopleData = defaults.data(forKey: "lastPlanPeople") { peopleToMeet = (try? JSONDecoder().decode([PersonRecommendation].self, from: peopleData)) ?? [] }
            messages.append(Message(text: "Your saved Universe plan is ready to review.", isUser: false, hasPlan: true))
        }
    }
    func updateProfile(_ profile: AttendeeProfile) {
        if Self.fingerprint(profile) != profileKey {
            reset()
            messages = []
        }
        self.profile = profile
    }
    func reset() { generation = UUID(); generatingRecommendations = false; recommendationWarnings = []; lastRankingRequest = "Recommend speaker sessions for both days"; work?.cancel(); busy = false; late = false; hasPlan = false; showPlan = false; sessions = []; sideEvents = []; peopleToMeet = []; prompt = ""; status = "Ready to plan" }
}

@MainActor enum SessionWarmup {
    private static var pending: Set<String> = []
    private static var completed: [String: Date] = [:]
    static func prepare(_ profile: AttendeeProfile) {
        let key = [profile.title ?? "", profile.background, profile.interests.sorted().joined(separator: "|")].joined(separator: "::")
        guard !pending.contains(key), completed[key].map({ Date().timeIntervalSince($0) < 3600 }) != true else { return }
        pending.insert(key)
        Task {
            defer { pending.remove(key) }
            do {
                var request = URLRequest(url: URL(string: "http://127.0.0.1:8765/session-plan")!)
                request.httpMethod = "POST"; request.timeoutInterval = 210
                request.setValue("application/json", forHTTPHeaderField: "Content-Type")
                let data = try JSONSerialization.jsonObject(with: JSONEncoder().encode(profile))
                request.httpBody = try JSONSerialization.data(withJSONObject: ["profile": data, "prompt": "Recommend speaker sessions for both days", "busy": [], "calendarConnected": false])
                let (_, response) = try await URLSession.shared.data(for: request)
                if (response as? HTTPURLResponse)?.statusCode == 200 { completed[key] = Date() }
            } catch { /* Foreground planning can retry; preparation never changes the user's plan. */ }
        }
    }
}
