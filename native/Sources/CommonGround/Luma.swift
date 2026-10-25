import SwiftUI

struct LumaEventDraft: Codable, Identifiable {
    let id, title, description, start, end, venueName, address, venueReason, sourceURL, status, visibility, demoEmail: String
    var url: String?
    var timeLabel: String {
        let f = DateFormatter(); f.timeZone = TimeZone(identifier: "America/Los_Angeles"); f.dateFormat = "MMM d · h:mm a"
        guard let startDate = ISO8601DateFormatter().date(from: start), let endDate = ISO8601DateFormatter().date(from: end) else { return start }
        let first = f.string(from: startDate); f.dateFormat = "h:mm a"
        return first + "–" + f.string(from: endDate) + " PT"
    }
}
struct DemoInviteContact: Decodable { let email: String; let demo: Bool }
struct LumaActionResult: Decodable { let status: String; var message: String?; var url: String?; var authURL: String?; var recipients: [String: DemoInviteContact]? }
struct LumaEventCard: View {
    let draft: LumaEventDraft
    var people: [PersonRecommendation] = []
    @State private var contacts: [String: DemoInviteContact] = [:]
    @State private var selected = Set<String>()
    @State private var selectionLoaded = false
    @State private var invitationsSubmitted = false
    @State private var invitationsNeedReview = false
    @State private var busy = false
    @State private var connected = false
    @Environment(\.scenePhase) private var scenePhase
    @State private var notice: String?
    @State private var eventURL: String?
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Private meetup", systemImage: "lock").font(.caption).foregroundStyle(.secondary)
            Text(draft.title).font(.headline)
            Label(draft.timeLabel, systemImage: "calendar")
            Label(draft.venueName, systemImage: "cup.and.saucer")
            Text(draft.address).font(.caption).foregroundStyle(.secondary)
            Text(draft.venueReason).font(.callout).fixedSize(horizontal: false, vertical: true)
            if let source = URL(string: draft.sourceURL) { Link("Venue & published hours", destination: source).font(.caption) }
            Text("Unlisted · Anyone with the link may view it").font(.caption).foregroundStyle(.secondary)
            if !people.isEmpty {
                Text("Invite recommended people").font(.headline)
                Text("Demo emails are linked to coworkers, not these public profiles.")
                    .font(.caption).foregroundStyle(.secondary)
                ForEach(people) { person in
                    Toggle(isOn: Binding(get: { selected.contains(person.id) }, set: { checked in
                        if checked { selected.insert(person.id) } else { selected.remove(person.id) }
                    })) {
                        VStack(alignment: .leading, spacing: 3) {
                            Text(person.name)
                            Text(contacts[person.id]?.email ?? "No demo email linked")
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }.toggleStyle(.checkbox)
                        .disabled(contacts[person.id] == nil || invitationsSubmitted || invitationsNeedReview)
                }
            }
            if let value = eventURL ?? draft.url, let url = URL(string: value) {
                Link(destination: url) { Label("Open on Luma", systemImage: "arrow.up.right") }.buttonStyle(.borderedProminent)
                if !people.isEmpty && !invitationsSubmitted && !invitationsNeedReview {
                    Button("Send invitations (\(selected.count))") { run("invite") }
                        .buttonStyle(.borderedProminent).disabled(selected.isEmpty)
                }
            } else {
                if !connected { Button("Connect Luma") { run("open") }.buttonStyle(.bordered) }
                else { Label("Luma connected", systemImage: "checkmark.circle").font(.caption).foregroundStyle(.secondary) }
                Button("Create private event") { run("create") }.buttonStyle(.borderedProminent).disabled(!connected)
            }
            if busy { ProgressView().controlSize(.small) }
            if let notice { Text(notice).font(.caption).foregroundStyle(.secondary) }
        }.padding(16).frame(maxWidth: .infinity, alignment: .leading)
            .background(Brand.paper, in: RoundedRectangle(cornerRadius: 12))
            .overlay(RoundedRectangle(cornerRadius: 12).strokeBorder(.quaternary))
            .disabled(busy)
            .task { await loadRecipients(); run("status") }
            .onChange(of: scenePhase) { _, phase in if phase == .active && !busy { run("status") } }
    }
    private func loadRecipients() async {
        guard !selectionLoaded else { return }
        do {
            var request = URLRequest(url: URL(string: "http://127.0.0.1:8765/luma")!)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONSerialization.data(withJSONObject: ["action": "recipients"])
            let (data, response) = try await URLSession.shared.data(for: request)
            guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw ProfileImportError.failed }
            contacts = try JSONDecoder().decode(LumaActionResult.self, from: data).recipients ?? [:]
            selected = Set(people.filter { contacts[$0.id] != nil }.map(\.id))
            selectionLoaded = true
        } catch { notice = "Couldn’t load linked emails. Reopen this card to try again." }
    }
    private func run(_ action: String) {
        busy = true; notice = nil
        Task {
            defer { busy = false }
            do {
                var req = URLRequest(url: URL(string: "http://127.0.0.1:8765/luma")!); req.httpMethod = "POST"; req.timeoutInterval = 180
                req.setValue("application/json", forHTTPHeaderField: "Content-Type")
                var body: [String: Any] = ["action":action,"draftID":draft.id]
                if action == "invite" { body["personIDs"] = Array(selected); body["confirmed"] = true }
                req.httpBody = try JSONSerialization.data(withJSONObject: body)
                let (data,response) = try await URLSession.shared.data(for:req)
                guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw ProfileImportError.failed }
                let result = try JSONDecoder().decode(LumaActionResult.self,from:data)
                if let message = result.message { notice = message }
                if let url = result.url { eventURL = url }
                if action == "invite" {
                    invitationsSubmitted = result.status == "invited"
                    invitationsNeedReview = result.status == "needs_review"
                }
                connected = result.status == "connected" || result.status == "created"
                if let value = result.authURL, let url = URL(string: value) { NSWorkspace.shared.open(url) }
            } catch {
                if action == "invite" { invitationsNeedReview = true; notice = "Couldn’t confirm delivery. Check Luma before trying again." }
                else { notice = "Couldn’t complete this step. Check Luma sign-in and try again." }
            }
        }
    }
}
