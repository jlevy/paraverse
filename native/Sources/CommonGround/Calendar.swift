import SwiftUI
import EventKit

@MainActor @Observable final class CalendarConnection {
    static let shared = CalendarConnection()
    let store = EKEventStore()
    var calendars: [EKCalendar] = []
    var message: String?
    var connected = UserDefaults.standard.bool(forKey: "calendarEnabled")
    var selectedID = UserDefaults.standard.string(forKey: "calendarID") ?? "" {
        didSet { UserDefaults.standard.set(selectedID, forKey: "calendarID") }
    }
    private init() { refresh() }
    var selected: EKCalendar? { calendars.first { $0.calendarIdentifier == selectedID } }
    func refresh() {
        guard connected else { calendars = []; return }
        guard EKEventStore.authorizationStatus(for: .event) == .fullAccess else { calendars = []; connected = false; message = "Allow calendar access again to reconnect this app build."; return }
        calendars = store.calendars(for: .event).sorted { $0.title < $1.title }
    }
    func connect() async {
        do {
            let granted = try await store.requestFullAccessToEvents()
            connected = granted; UserDefaults.standard.set(granted, forKey: "calendarEnabled")
            if granted { refresh(); message = nil }
            else { message = "Calendar access is off. Enable it in System Settings → Privacy & Security → Calendars." }
        } catch { message = error.localizedDescription }
    }
    func disconnect() { connected = false; selectedID = ""; calendars = []; UserDefaults.standard.set(false, forKey: "calendarEnabled") }
    func events(from start: Date, to end: Date) -> [EKEvent] {
        guard connected, let selected else { return [] }
        return store.events(matching: store.predicateForEvents(withStart: start, end: end, calendars: [selected])).sorted { $0.startDate < $1.startDate }
    }
}

struct CalendarSettings: View {
    @AppStorage("paraverse.interfaceSoundsMuted") private var soundsMuted = false
    @State private var connection = CalendarConnection.shared
    var body: some View {
        Form {
            Section("Sound") {
                Toggle("Mute button sounds", isOn: $soundsMuted)
            }
            Section("Google Calendar") {
                Text("Use your Google account through macOS Calendar. Add the account in Internet Accounts and turn on Calendars.").foregroundStyle(.secondary)
                Button("Add Google account in System Settings…") {
                    NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.Internet-Accounts-Settings.extension")!)
                }
                if !connection.connected {
                    Button("Allow calendar access") { Task { await connection.connect() } }.buttonStyle(.borderedProminent).tint(Brand.primaryAction)
                } else {
                    Picker("Calendar for your plans", selection: $connection.selectedID) {
                        Text("Choose a calendar").tag("")
                        ForEach(connection.calendars, id: \.calendarIdentifier) { calendar in
                            Text("\(calendar.title) · \(calendar.source.title)\(calendar.allowsContentModifications ? "" : " (read-only)")").tag(calendar.calendarIdentifier)
                        }
                    }
                    HStack { Button("Refresh calendars") { connection.refresh() }; Button("Disconnect") { connection.disconnect() } }
                    Text("Paraverse reads the selected calendar for planning. Events are saved only when you choose Save. Disconnecting does not remove existing events.").font(.caption).foregroundStyle(.secondary)
                }
                if let message = connection.message { Text(message).foregroundStyle(.secondary) }
            }
        }.formStyle(.grouped).onAppear { connection.refresh() }
        .onReceive(NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification)) { _ in connection.refresh() }
    }
}

extension EKEvent {
    var occurrenceKey: String { calendarItemIdentifier + "|" + String((occurrenceDate ?? startDate).timeIntervalSince1970) }
}

private struct CalendarEdit: Identifiable { let id = UUID(); var event: EKEvent? }
struct CalendarPage: View {
    @State private var connection = CalendarConnection.shared
    @State private var events: [EKEvent] = []
    @State private var edit: CalendarEdit?
    @State private var deleting: EKEvent?
    @State private var message: String?
    @State private var day = Date()
    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Make room for what matters.").font(.system(size: 28, weight: .medium, design: .serif))
                    Text(connection.selected?.title ?? "Connect a calendar to start planning.").foregroundStyle(.secondary)
                }
                Spacer()
                SettingsLink { Label("Calendar settings", systemImage: "gearshape") }
                Button("New event", systemImage: "plus") { edit = CalendarEdit() }.disabled(connection.selected?.allowsContentModifications != true)
            }
            if connection.selected == nil {
                ContentUnavailableView("Choose your calendar", systemImage: "calendar", description: Text("Open Calendar settings, allow access, and choose your Google calendar."))
            } else {
                HStack { DatePicker("Starting", selection: $day, displayedComponents: .date); Text("Next 30 days").foregroundStyle(.secondary); Spacer(); Button("Refresh") { reload() } }
                if let message { Text(message).foregroundStyle(.secondary) }
                List {
                    ForEach(events, id: \.occurrenceKey) { event in
                        HStack(spacing: 16) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(event.title ?? "Untitled event").font(.headline)
                                Text(event.startDate.formatted(date: .abbreviated, time: event.isAllDay ? .omitted : .shortened)).foregroundStyle(.secondary)
                                if let location = event.location, !location.isEmpty { Text(location).font(.caption).foregroundStyle(.secondary) }
                            }
                            Spacer()
                            Button("Edit") { edit = CalendarEdit(event: event) }.disabled(!event.calendar.allowsContentModifications)
                            Button(role: .destructive) { deleting = event } label: { Image(systemName: "trash") }.disabled(!event.calendar.allowsContentModifications).accessibilityLabel("Delete \(event.title ?? "event")")
                        }.padding(.vertical, 8)
                    }
                }.overlay { if events.isEmpty { ContentUnavailableView("Nothing scheduled", systemImage: "calendar", description: Text("Add an event or choose another starting date.")) } }
            }
        }.padding(28).background(Brand.paper)
        .onAppear { connection.refresh(); reload() }
        .onChange(of: day) { reload() }
        .onChange(of: connection.selectedID) { reload() }
        .onReceive(NotificationCenter.default.publisher(for: .EKEventStoreChanged)) { _ in connection.refresh(); reload() }
        .sheet(item: $edit) { item in CalendarEventEditor(event: item.event) { reload() } }
        .alert("Delete this event?", isPresented: Binding(get: { deleting != nil }, set: { if !$0 { deleting = nil } })) {
            Button("Cancel", role: .cancel) { deleting = nil }
            Button("Delete", role: .destructive) {
                if let event = deleting {
                    do { try connection.store.remove(event, span: .thisEvent); reload() }
                    catch { message = error.localizedDescription }
                }
                deleting = nil
            }
        } message: { Text("This occurrence will be removed from your calendar and synced to its account. If it has guests, your calendar provider may notify them.") }
    }
    private func reload() { events = connection.events(from: Calendar.current.startOfDay(for: day), to: Calendar.current.date(byAdding: .day, value: 30, to: day)!) }
}

struct CalendarEventEditor: View {
    var event: EKEvent?
    var saved: () -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var title = ""
    @State private var start = Date()
    @State private var end = Date().addingTimeInterval(3600)
    @State private var allDay = false
    @State private var location = ""
    @State private var notes = ""
    @State private var error: String?
    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text(event == nil ? "New event" : "Edit event").font(.title2)
            Form {
                TextField("Title", text: $title)
                Toggle("All day", isOn: $allDay)
                DatePicker("Starts", selection: $start)
                DatePicker("Ends", selection: $end)
                TextField("Location", text: $location)
                TextField("Notes", text: $notes, axis: .vertical).lineLimit(2...5)
            }
            Text("Saving updates your selected calendar. For repeating events, only this occurrence changes. Existing guests may receive updates from your calendar provider.").font(.caption).foregroundStyle(.secondary)
            if let error { Text(error).foregroundStyle(.red) }
            HStack { Button("Cancel") { dismiss() }.keyboardShortcut(.cancelAction); Spacer(); Button("Save") { commit() }.buttonStyle(.borderedProminent).tint(Brand.primaryAction).disabled(title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || end <= start).keyboardShortcut(.defaultAction) }
        }.padding(28).frame(width: 490)
        .onAppear { if let event { title = event.title ?? ""; start = event.startDate; end = event.endDate; allDay = event.isAllDay; location = event.location ?? ""; notes = event.notes ?? "" } }
    }
    private func commit() {
        let connection = CalendarConnection.shared
        guard connection.connected, let calendar = event?.calendar ?? connection.selected, calendar.allowsContentModifications else { error = "Choose a writable calendar in Settings."; return }
        let value = event ?? EKEvent(eventStore: connection.store)
        value.calendar = calendar; value.title = title; value.startDate = start; value.endDate = end; value.isAllDay = allDay; value.location = location; value.notes = notes
        do { try connection.store.save(value, span: .thisEvent); saved(); dismiss() }
        catch { self.error = error.localizedDescription; connection.store.refreshSourcesIfNecessary() }
    }
}

extension CalendarConnection {
    func saveSessions(_ sessions: [PlannedSession]) throws -> Int {
        refresh()
        func failure(_ message: String) -> NSError { NSError(domain: "CommonGround.Calendar", code: 1, userInfo: [NSLocalizedDescriptionKey: message]) }
        guard let calendar = selected, calendar.allowsContentModifications else { throw failure("Choose a writable calendar in Settings first.") }
        var pending: [EKEvent] = []
        for session in sessions {
            let marker = "Paraverse session: \(session.id)"
            let existing = events(from: session.startDate, to: session.endDate)
            if existing.contains(where: { ($0.notes ?? "").contains(marker) || ($0.notes ?? "").contains("Common Ground session: \(session.id)") }) { continue }
            if existing.contains(where: { $0.availability != .free && $0.startDate < session.endDate && $0.endDate > session.startDate }) {
                throw failure("\(session.title) overlaps an event in your calendar. Replan or remove that session before saving.")
            }
            if pending.contains(where: { $0.startDate < session.endDate && $0.endDate > session.startDate }) { throw failure("Two sessions overlap. Replan before saving.") }
            let event = EKEvent(eventStore: store); event.calendar = calendar
            event.title = session.title; event.startDate = session.startDate; event.endDate = session.endDate
            event.timeZone = TimeZone(identifier: "America/Los_Angeles"); event.location = session.location
            event.url = URL(string: session.sourceURL)
            event.notes = marker + "\n" + session.speakers + "\n" + session.reason
            pending.append(event)
        }
        do {
            for event in pending { try store.save(event, span: .thisEvent, commit: false) }
            try store.commit()
        } catch { store.reset(); throw error }
        return pending.count
    }
}
