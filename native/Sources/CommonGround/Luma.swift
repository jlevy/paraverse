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
    let people: [PersonRecommendation]
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
        VStack(alignment: .leading, spacing: 16) {
            Label("Private meetup", systemImage: "lock").font(.caption).foregroundStyle(.secondary)
            Text(draft.title).font(.system(size: 18, weight: .bold, design: .monospaced))
            Label(draft.timeLabel, systemImage: "calendar")
            Label(draft.venueName, systemImage: "cup.and.saucer")
            Text(draft.address).font(.caption).foregroundStyle(.secondary)
            Text("Unlisted · Anyone with the link may view it")
                .font(.caption).foregroundStyle(.secondary)
            DisclosureGroup("Venue details") {
                VStack(alignment: .leading, spacing: 8) {
                    Text(draft.venueReason).font(.callout).fixedSize(horizontal: false, vertical: true)
                    if let source = URL(string: draft.sourceURL) { Link("Venue & hours ↗", destination: source) }
                }.padding(.top, 8)
            }.tint(Brand.welcomeSubtitle)
            if !people.isEmpty {
                Text("Invite recommended people").font(.headline)
                Text("Demo emails are linked to coworkers, not these public profiles.")
                    .font(.caption).foregroundStyle(.secondary)
                if !selectionLoaded {
                    ThinkingStatus(text: "Loading invite options…")
                } else {
                    VStack(spacing: 8) {
                        ForEach(people) { person in recipientRow(person) }
                    }
                }
            }

            if let value = eventURL ?? draft.url, let url = URL(string: value) {
                Link(destination: url) { Label("Open on Luma", systemImage: "arrow.up.right") }.buttonStyle(WorldButtonStyle(teal: true))
                if !people.isEmpty && !invitationsSubmitted && !invitationsNeedReview {
                    Button("Send invitations (\(selected.count))") { run("invite") }
                        .buttonStyle(WorldButtonStyle(teal: true)).disabled(selected.isEmpty)
                }
            } else {
                if !connected { Button("Connect Luma") { run("open") }.buttonStyle(PlannerQuietButtonStyle()) }
                else { Label("Luma connected", systemImage: "checkmark.circle").font(.caption).foregroundStyle(.secondary) }
                Button("Create private event") { run("create") }.buttonStyle(WorldButtonStyle(teal: true)).disabled(!connected)
            }
            if busy { ThinkingStatus(text: "Updating your meetup…") }
            if let notice { Text(notice).font(.caption).foregroundStyle(.secondary) }
        }.padding(20).frame(maxWidth: .infinity, alignment: .leading)
            .foregroundStyle(Brand.welcomeTitle)
            .background(PixelPanel().fill(Color(red: 0.12, green: 0.15, blue: 0.19)))
            .overlay(PixelPanel().stroke(Brand.fieldBorder, lineWidth: 1))
            .disabled(busy)
            .task { await loadRecipients(); run("status") }
            .onChange(of: scenePhase) { _, phase in if phase == .active && !busy { run("status") } }
    }
    private func recipientRow(_ person: PersonRecommendation) -> some View {
        let checked = selected.contains(person.id)
        let available = contacts[person.id] != nil
        return Button {
            if checked { selected.remove(person.id) } else { selected.insert(person.id) }
        } label: {
            HStack(spacing: 12) {
                ZStack {
                    PixelPanel().fill(checked ? Brand.buttonSecondary : Color.clear)
                    PixelPanel().stroke(Brand.fieldBorder, lineWidth: 1)
                    if checked { Image(systemName: "checkmark").font(.system(size: 12, weight: .bold)) }
                }.frame(width: 22, height: 22)
                if let sprite = WorldCharacter.recommendationImage(for: person.id) {
                    Image(nsImage: sprite).resizable().interpolation(.none).scaledToFit()
                        .frame(width: 40, height: 48).accessibilityHidden(true)
                }
                VStack(alignment: .leading, spacing: 4) {
                    Text(person.name).font(.system(size: 13, weight: .bold, design: .monospaced))
                    Text(contacts[person.id]?.email ?? "No demo email linked")
                        .font(.system(size: 11)).foregroundStyle(Brand.welcomeSubtitle)
                }
                Spacer(minLength: 0)
            }.padding(12).frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                .background(PixelPanel().fill(checked ? Color.teal.opacity(0.14) : Color.black.opacity(0.12)))
                .overlay(PixelPanel().stroke(checked ? Color.teal : Brand.fieldBorder.opacity(0.4), lineWidth: 1))
        }
        .buttonStyle(.plain)
        .disabled(!available || invitationsSubmitted || invitationsNeedReview)
        .accessibilityLabel("\(person.name), \(contacts[person.id]?.email ?? "No demo email linked")")
        .accessibilityValue(checked ? "Selected" : "Not selected")
        .accessibilityAddTraits(checked ? .isSelected : [])
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
        } catch { selectionLoaded = true; notice = "Couldn’t load linked emails. Reopen this card to try again." }
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

// Shared construction keeps both chat surfaces on the same recipient inputs.
extension Message {
    var meetupCard: LumaEventCard? { eventDraft.map { LumaEventCard(draft: $0, people: eventPeople) } }
}
