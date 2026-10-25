import SwiftUI
import AppKit
import UniformTypeIdentifiers

@MainActor final class CommonGroundDelegate: NSObject, NSApplicationDelegate {
    func applicationWillFinishLaunching(_ notification: Notification) {
        // Keep native windows, panels and controls dark regardless of macOS appearance.
        NSApplication.shared.appearance = NSAppearance(named: .darkAqua)
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        if let url = Bundle.main.url(forResource: "Paraverse", withExtension: "icns"), let icon = NSImage(contentsOf: url) {
            NSApplication.shared.applicationIconImage = icon
        }
    }
}

@main struct CommonGroundApp: App {
    @AppStorage("paraverse.interfaceSoundsMuted") private var soundsMuted = false
    @NSApplicationDelegateAdaptor(CommonGroundDelegate.self) private var appDelegate
    @State private var planner = Planner()
    @State private var profileStore = ProfileStore()
    var body: some Scene {
        Window("Paraverse", id: "main") {
            AppRoot(store: profileStore, planner: planner)
                .preferredColorScheme(.dark)
                .tint(Brand.olive)
                .frame(minWidth: 900, minHeight: 620)
        }
        .defaultSize(width: 1180, height: 800)
        .windowToolbarStyle(.unified)
        .commands {
            CommandMenu("Sound") {
                Toggle("Mute Button Sounds", isOn: $soundsMuted)
            }
            CommandMenu("Profile") {
                Button("Edit Profile…") { profileStore.editing = true }.disabled(profileStore.stage != 4)
                Button("Try Another Profile…") { planner.reset(); planner.messages = []; profileStore.startNewProfile() }
                Button("Restore Previous Profile") { profileStore.restorePrevious(); planner.start(for: profileStore.profile) }.disabled(!profileStore.canRestorePrevious)
                Divider()
                Button("Replay Onboarding") { profileStore.stage = 0 }
                Button("Log Out") { profileStore.logOut(); planner.reset(); planner.messages = [] }.disabled(profileStore.stage != 4)
            }
            CommandGroup(after: .newItem) {
                Button("Reset Demo") { planner.reset() }.keyboardShortcut("n", modifiers: [.command, .shift])
            }
            CommandMenu("Plan") {
                Button(planner.showPlan ? "Hide Plan" : "Show Plan") { planner.showPlan.toggle() }.keyboardShortcut("p", modifiers: [.command, .shift])
                Button("Refresh External Events") { planner.refreshExternalEvents() }.disabled(planner.busy)
                Button("Refresh People Recommendations") { planner.refreshPeople() }.disabled(planner.busy)
                Button("Recommend Sessions") { planner.generate() }.keyboardShortcut("g", modifiers: [.command, .shift]).disabled(planner.busy)
                Button("Arrive After 3 PM") { planner.send("I can only arrive after 3 PM.") }.keyboardShortcut("l", modifiers: [.command, .shift]).disabled(planner.busy)
            }
        }
        Settings { CalendarSettings().preferredColorScheme(.dark).frame(width: 560, height: 400) }
    }
}

struct CompanionMark: View {
    var size: CGFloat = 34
    var body: some View {
        PixelPlanet()
            .padding(size * 0.18).frame(width: size, height: size)
            .background(Brand.paper, in: RoundedRectangle(cornerRadius: size * 0.27))
            .accessibilityHidden(true)
    }
}
enum DetailSheet: String, Identifiable { case group, conference, calendar; var id: String { rawValue } }

struct ContentView: View {
    @Bindable var planner: Planner
    var profile: AttendeeProfile
    var logOut: () -> Void
    var editProfile: () -> Void
    var saveProfile: (AttendeeProfile) -> Void
    @State private var sheet: DetailSheet?
    @State private var calendarSelection: [PlannedSession]?
    @State private var showConnections = false
    @State private var showConference = false
    @State private var assistantOpen = false
    @State private var conferenceTab = "Overview"
    @State private var selectedCompanion: String? = "discover"
    @State private var sidebarOpen = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    var body: some View {
        HStack(spacing: 0) {
            if sidebarOpen {
            VStack(alignment: .leading, spacing: 0) {
                HStack(spacing: 8) {
                    CompanionMark(size: 24)
                    Text("Paraverse").font(.system(size: 13, weight: .semibold, design: .rounded))
                }.padding(.horizontal, 16).padding(.top, 8).padding(.bottom, 8)
                List(selection: $selectedCompanion) {
                    Section {
                        if universeSaved {
                            Label("Conference world", systemImage: "map").tag("upcoming")
                        }
                        Label("Discover", systemImage: "safari").tag("discover")
                    }
                    if universeSaved || planner.hasPlan {
                        Section("My conferences") {
                            Label("GitHub Universe", systemImage: "building.2").tag("universe")
                        }
                    }
                    Section("Workspace") {
                        Label("Calendar", systemImage: "calendar.badge.clock").tag("calendar")
                    }
                }
                .listStyle(.sidebar)
                .labelStyle(GroundSidebarLabelStyle())
                .environment(\.defaultMinListRowHeight, 28)
                .font(.system(size: 13))
                VStack(alignment: .leading, spacing: 8) {
                    Divider()
                    Button { selectedCompanion = "profile"; planner.showPlan = false } label: { HStack(spacing: 8) {
                        ProfileAvatar(profile: profile, size: 28)
                        Text(profile.name).font(.system(size: 13))
                        Spacer()
                        Image(systemName: "pencil").foregroundStyle(.secondary)
                    } }.buttonStyle(.plain).help("Your profile")
                    Button(action: logOut) {
                        Label("Log Out", systemImage: "rectangle.portrait.and.arrow.right")
                            .font(.system(size: 13))
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.vertical, 6)
                            .contentShape(Rectangle())
                    }.buttonStyle(.plain).foregroundStyle(.secondary)
                        .help("Return to the welcome screen")
                }.padding(.horizontal, 16).padding(.bottom, 12)
            }
            .frame(width: 220)
            Divider()
            }
            Group {
                if selectedCompanion == "upcoming" {
                    UniverseWorld(
                        profile: profile, planner: planner, assistantOpen: $assistantOpen, saveCalendar: { sessions in calendarSelection = sessions; sheet = .calendar },
                        openSchedule: { selectedCompanion = "universe"; conferenceTab = "Schedule" },
                        openPeople: { selectedCompanion = "universe"; conferenceTab = "Attendees" },
                        openAssistant: { assistantOpen = true },
                        openDiscovery: { selectedCompanion = "discover" }
                    )
                } else if selectedCompanion == "discover" {
                    GeometryReader { viewport in
                    ScrollView {
                        VStack(alignment: .leading, spacing: 32) {
                            VStack(alignment: .leading, spacing: 16) {
                                Text("Conferences for you").font(.system(size: 26, weight: .bold, design: .monospaced))
                                HStack(alignment: .center, spacing: 8) {
                                    if profile.travel != "Online" {
                                        DiscoveryLocationPin()
                                            .frame(width: 12, height: 16)
                                            .accessibilityHidden(true)
                                    }
                                    Text(profile.travel == "Online" ? "Online conferences" : (profile.city.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() == "san francisco" ? "San Francisco, CA" : profile.city))
                                        .font(.system(size: 13))
                                        .foregroundStyle(Brand.welcomeSubtitle)
                                }
                            }
                            ConferenceCards(profile: Binding(get: { profile }, set: { saveProfile($0) }), openConference: { selectedCompanion = "upcoming" })
                        }
                        .padding(.horizontal, 24)
                        .padding(.vertical, 64)
                        .frame(maxWidth: 960, alignment: .leading)
                        .frame(maxWidth: .infinity, minHeight: viewport.size.height, alignment: .center)
                    }
                    }.background { Brand.welcomeBackground }
                } else if selectedCompanion == "profile" {
                    YourProfileView(profile: profile, save: saveProfile)
                } else if selectedCompanion == "calendar" { CalendarPage()
                } else { conferenceWorkspace }
            }.frame(minWidth: 330, maxWidth: .infinity)
            .inspector(isPresented: Binding(get: { assistantOpen && selectedCompanion != "upcoming" }, set: { assistantOpen = $0 })) {
                VStack(spacing: 0) {
                    HStack {
                        Text("Universe assistant").font(.headline)
                        Spacer()
                        Button { assistantOpen = false } label: { Image(systemName: "xmark") }
                            .buttonStyle(.plain).help("Close assistant").accessibilityLabel("Close assistant")
                    }.padding(GroundLayout.chatInset)
                    Divider()
                    chat
                }.inspectorColumnWidth(min: 340, ideal: 400, max: 520)
            }
            .navigationTitle(selectedCompanion == "profile" ? "Your profile" : selectedCompanion == "calendar" ? "Calendar" : selectedCompanion == "upcoming" ? "Conference world" : selectedCompanion == "discover" ? "Discover" : "GitHub Universe")
            .toolbar(removing: .sidebarToggle)
            .toolbar {
                ToolbarItem(placement: .navigation) {
                    Button { sidebarOpen.toggle() } label: {
                        Image(systemName: "sidebar.left")
                    }
                    .accessibilityLabel(sidebarOpen ? "Hide sidebar" : "Show sidebar")
                    .help(sidebarOpen ? "Hide sidebar" : "Show sidebar")
                }
                ToolbarItemGroup(placement: .primaryAction) {
                    SettingsLink { Label("Settings", systemImage: "gearshape") }
                }
            }
        }
        .toolbar(removing: .sidebarToggle)
        .onAppear { sidebarOpen = false }
        .onChange(of: selectedCompanion) { _, _ in sidebarOpen = false }
        .onChange(of: profile) { _, value in planner.updateProfile(value) }
        .onChange(of: planner.showPlan) { _, shown in
            if shown {
                if selectedCompanion == "upcoming" { assistantOpen = true }
                else { selectedCompanion = "universe"; conferenceTab = "Schedule"; planner.showPlan = false }
            }
        }
        .sheet(item: $sheet) { item in sheetContent(item).padding(28).frame(width: 470) }
    }

    private var universeSaved: Bool {
        profile.status(for: "universe-2026") != .none
    }

    private var conferenceWorkspace: some View {
        VStack(spacing: 0) {
            HStack {
                Picker("Conference section", selection: $conferenceTab) {
                    ForEach(["Overview", "Schedule", "Attendees"], id: \.self) { Text($0).tag($0) }
                }.pickerStyle(.segmented).labelsHidden().frame(maxWidth: 420, alignment: .leading)
                Spacer()
            }.frame(maxWidth: .infinity, alignment: .leading).padding(.horizontal, GroundLayout.pageInset).padding(.vertical, 20)
                .frame(maxWidth: GroundLayout.detailWidth, alignment: .leading).frame(maxWidth: .infinity)
            Divider()
            if conferenceTab == "Schedule" {
                if !planner.hasPlan {
                    VStack(spacing: 18) {
                        ContentUnavailableView("Make time for what matters", systemImage: "calendar", description: Text("Find speaker sessions around your interests and availability."))
                        Button("Plan with assistant") { assistantOpen = true }.buttonStyle(.borderedProminent).tint(Brand.primaryAction)
                    }.frame(maxWidth: .infinity, maxHeight: .infinity)
                } else { plan.frame(maxWidth: GroundLayout.detailWidth).frame(maxWidth: .infinity) }
            } else if conferenceTab == "Attendees" {
                AttendeesPage()
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 24) {
                        Text("GitHub Universe").font(.system(size: 36, weight: .medium, design: .serif))
                        Text("Two days of building what’s next.").font(.title3).foregroundStyle(.secondary)
                        Label("October 28–29, 2026 · Pacific time", systemImage: "calendar")
                        Label("Fort Mason Center · San Francisco", systemImage: "mappin.and.ellipse")
                        Text("Explore the sessions, find your people, and make a plan that fits your day.").foregroundStyle(.secondary)
                        HStack {
                            Button(planner.hasPlan ? "View your schedule" : "Plan my sessions") {
                                conferenceTab = "Schedule"
                                if !planner.hasPlan { assistantOpen = true }
                            }.buttonStyle(.borderedProminent).tint(Brand.primaryAction)
                            Button("See who’s going") { conferenceTab = "Attendees" }.buttonStyle(.bordered)
                        }
                        Divider()
                        Text("Attendance").font(.headline)
                        Text("In person: $1,399 · Virtual: free").foregroundStyle(.secondary)
                        Link("Conference website", destination: URL(string: "https://githubuniverse.com/")!)
                        if planner.hasPlan {
                            Label("\(planner.sessions.count) sessions in your plan", systemImage: "checkmark.circle").foregroundStyle(Brand.olive)
                        }
                    }.padding(GroundLayout.pageInset).frame(maxWidth: GroundLayout.detailWidth, alignment: .leading).frame(maxWidth: .infinity)
                }
            }
        }.background(Brand.canvas)
    }

    private var chat: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 27) {
                        HStack { Spacer(); Text("GITHUB UNIVERSE · OCT 28–29").font(.caption2.weight(.medium)).tracking(1.2).foregroundStyle(.secondary); Spacer() }.padding(.top, 28)
                        ForEach(planner.messages) { message in
                            VStack(alignment: .leading, spacing: 13) {
                                if message.isUser {
                                    HStack { Spacer(minLength: 36); Text(message.text).padding(15).background(Brand.sage, in: RoundedRectangle(cornerRadius: 16)).textSelection(.enabled) }
                                } else {
                                    HStack(alignment: .top, spacing: 12) { CompanionMark(size: 25); Text(.init(message.text)).lineSpacing(5).textSelection(.enabled) }
                                }
                                if let draft = message.eventDraft { LumaEventCard(draft: draft) }
                                SidebarEventCards(sessions: message.eventSessions) { sessions in
                                    calendarSelection = sessions
                                    sheet = .calendar
                                }
                                ForEach(message.recommendations) { person in
                                    MeetPersonCard(person: person)
                                }
                                if !message.recommendations.isEmpty {
                                    Text("Attendance is self-reported · Matching opt-in not confirmed")
                                        .font(.caption2).foregroundStyle(.secondary)
                                }
                                if message.hasPlan {
                                    GroundPlanLink { selectedCompanion = "universe"; conferenceTab = "Schedule" }.padding(.leading, 37)
                                }
                            }.id(message.id)
                        }
                        if !planner.hasPlan && !planner.busy {
                            Button { planner.generate() } label: { Label("Put my day together", systemImage: "calendar.badge.plus") }.buttonStyle(.borderedProminent).tint(Brand.primaryAction).controlSize(.regular).padding(.leading, 37)
                        }
                        if planner.busy { HStack { ProgressView().controlSize(.small); Text(planner.status).font(.caption).foregroundStyle(.secondary) }.padding(.leading, 37) }
                        Color.clear.frame(height: 1).id("bottom")
                    }.font(.system(size: 14)).padding(.horizontal, GroundLayout.chatInset).padding(.bottom, 25).frame(maxWidth: 700)
                }
                .onChange(of: planner.messages.count) { _, _ in proxy.scrollTo("bottom", anchor: .bottom) }
                .onChange(of: planner.busy) { _, _ in proxy.scrollTo("bottom", anchor: .bottom) }
            }
            VStack(alignment: .leading, spacing: 12) {
                if planner.hasPlan && !planner.late {
                    Button { planner.send("I can only arrive after 3 PM.") } label: { HStack { Text("I can only arrive after 3 PM"); Image(systemName: "arrow.up.left") }.font(.caption) }.buttonStyle(.bordered).disabled(planner.busy)
                }
                HStack(alignment: .bottom, spacing: 10) {
                    TextField("Make room for what matters…", text: $planner.prompt, axis: .vertical).lineLimit(1...5).textFieldStyle(.plain).font(.system(size: 14)).padding(.vertical, 8).onSubmit { planner.send() }.accessibilityLabel("Message your conference companion")
                    Button { planner.send() } label: { Image(systemName: "arrow.up").font(.system(size: 14, weight: .semibold)).frame(width: 28, height: 28) }.buttonStyle(.plain).foregroundStyle(Brand.paper).background(Brand.olive, in: Circle()).clipShape(Circle()).disabled(planner.busy || planner.prompt.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty).help("Send message").accessibilityLabel("Send message")
                }.padding(12).background(.background, in: RoundedRectangle(cornerRadius: 15)).overlay(RoundedRectangle(cornerRadius: 15).stroke(.quaternary))
            }.padding(GroundLayout.chatInset)
        }.background(Brand.paper)
    }

    private var plan: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                Text("Recommendations for you").font(.title2.weight(.semibold))
                Text("October 28–29 · Pacific time").font(.caption).foregroundStyle(.secondary)
                if !planner.hasPlan {
                    ContentUnavailableView("Plan your conference", systemImage: "calendar", description: Text("Ask for speaker sessions that fit your interests."))
                } else {
                    ForEach(Array(Set(planner.sessions.map(\.day))).sorted(), id: \.self) { day in
                        VStack(alignment: .leading, spacing: 18) {
                            Text(["2026-10-26":"Monday, October 26", "2026-10-27":"Tuesday, October 27", "2026-10-28":"Wednesday, October 28", "2026-10-29":"Thursday, October 29"][day] ?? day).font(.headline)
                            ForEach(planner.sessions.filter { $0.day == day }) { session in
                                VStack(alignment: .leading, spacing: 7) {
                                    Text(session.time).font(.caption.weight(.semibold)).foregroundStyle(Brand.olive)
                                    Text(session.title).font(.headline)
                                    Text(session.speakers).font(.subheadline)
                                    Text(session.location).font(.caption).foregroundStyle(.secondary)
                                    Text(session.reason).font(.callout).foregroundStyle(.secondary)
                                    HStack {
                                        if let url = URL(string: session.sourceURL) { Link("Session details", destination: url) }
                                        Spacer()
                                        Button("Add to calendar") { calendarSelection = [session]; sheet = .calendar }.buttonStyle(.borderless)
                                    }.font(.caption)
                                }
                                Divider()
                            }
                        }
                    }
                    if planner.sideEvents.isEmpty {
                        Button("Find external events", systemImage: "sparkle.magnifyingglass") { planner.send("Suggest external events that fit my profile and session plan") }.disabled(planner.busy)
                    } else {
                        Text("Around Universe").font(.headline)
                        Text("Optional alternatives. Choose the events you want to add.").font(.caption).foregroundStyle(.secondary)
                        ForEach(planner.sideEvents) { event in
                            VStack(alignment: .leading, spacing: 7) {
                                Text(event.title).font(.headline)
                                Text("\(event.day) · \(event.time)").font(.caption).foregroundStyle(Brand.olive)
                                Text("\(event.speakers) · \(event.location)").font(.caption)
                                Text(event.reason).font(.callout).foregroundStyle(.secondary)
                                Text("Price not confirmed — check the organizer").font(.caption).foregroundStyle(.secondary)
                                Text("Advance registration required").font(.caption).foregroundStyle(.secondary)
                                if let url = URL(string: event.sourceURL) { Link("Check registration", destination: url) }
                                Button("Add to calendar") { calendarSelection = [event]; sheet = .calendar }
                            }
                            Divider()
                        }
                    }
                    if !planner.calendarChecked { Text("Availability hasn’t been checked. Connect your calendar in Settings.").font(.caption).foregroundStyle(.secondary) }
                    Button(planner.savedToCalendar ? "Saved to calendar" : "Add all to calendar", systemImage: planner.savedToCalendar ? "checkmark.circle" : "calendar.badge.plus") { calendarSelection = nil; sheet = .calendar }.buttonStyle(.borderedProminent).tint(Brand.primaryAction).disabled(planner.sessions.isEmpty || planner.savedToCalendar)
                }
            }.padding(GroundLayout.pageInset)
        }.background(Brand.canvas)
        .onAppear { planner.updateProfile(profile) }
        .onChange(of: profile) { _, value in planner.updateProfile(value) }
    }

    private var groupCard: some View {
        VStack(alignment: .leading, spacing: 15) {
            Text("GOOD COMPANY").font(.caption2.weight(.medium)).tracking(1.2).foregroundStyle(.secondary)
            HStack(spacing: -5) { ForEach(["JL", "AC", "MR", "SK"], id: \.self) { initials in GroundAvatar(initials: initials, isCurrentUser: initials == "JL") } }
            Text("People who build with a designer’s eye.").font(.system(size: 22, weight: .medium, design: .serif))
            ForEach(["Alex Chen · Design engineer", "Maya Rivera · Product designer", "Sam Kim · Frontend engineer"], id: \.self) { name in Text(name).font(.caption).foregroundStyle(.secondary) }
            DisclosureGroup("Why this group?", isExpanded: $showConnections) {
                VStack(alignment: .leading, spacing: 12) {
                    Label("You and Alex share an interest in design systems.", systemImage: "point.3.connected.trianglepath.dotted")
                    Label("Your design feedback can help Sam’s prototype.", systemImage: "arrow.left.arrow.right")
                    Label("You and Maya are exploring AI tools.", systemImage: "person.2")
                    Text("Everyone is available at \(planner.late ? "4:30 PM" : "2 PM").").foregroundStyle(.secondary)
                }.font(.callout).padding(.top, 12)
            }
        }
    }

    @ViewBuilder private func sheetContent(_ item: DetailSheet) -> some View {
        VStack(alignment: .leading, spacing: 18) {
            switch item {
            case .group:
                Label("The connections behind your group", systemImage: "person.3").font(.title2.weight(.semibold))
                Text("Illustrative relationships between sample attendees. Live graph evidence will come from FalkorDB.").foregroundStyle(.secondary)
                ForEach(["You → Design systems ← Alex", "You → Offer design feedback → Sam’s prototype", "Maya → Explores AI tools ← You"], id: \.self) { path in Text(path).font(.callout).padding(13).frame(maxWidth: .infinity, alignment: .leading).background(.quaternary, in: RoundedRectangle(cornerRadius: 9)) }
                Text("Shared availability: \(planner.late ? "4:30–5:00 PM" : "2:00–2:30 PM") on October 28.").font(.callout)
            case .conference:
                Text("GitHub Universe 2026").font(.title2.weight(.semibold))
                Label("October 28–29, 2026", systemImage: "calendar")
                Label("Fort Mason Center, San Francisco", systemImage: "mappin.and.ellipse")
                Text("Previously retrieved pricing: $1,399 in person; virtual attendance is free. Confirm current pricing on the official website.").foregroundStyle(.secondary)
                Link("Official conference website ↗", destination: URL(string: "https://githubuniverse.com/")!)
                Text("Session recommendations use the official Universe catalog.").font(.caption).foregroundStyle(.secondary)
            case .calendar:
                Text("Add to calendar").font(.title2.weight(.semibold))
                if CalendarConnection.shared.selected == nil {
                    Text("Choose a calendar in Settings, then return to add your events.")
                    SettingsLink { Label("Calendar settings", systemImage: "gearshape") }
                } else {
                    Text("Save \((calendarSelection ?? planner.sessions).count) events to \(CalendarConnection.shared.selected!.title). Conflicts are checked again before saving.")
                }
                Text("This adds personal calendar events. It does not register you for events.").foregroundStyle(.secondary)
            }
            HStack { Spacer(); Button(item == .calendar ? "Cancel" : "Close") { sheet = nil; showConference = false }.keyboardShortcut(.cancelAction); if item == .calendar && CalendarConnection.shared.selected != nil { Button("Add to calendar") { sheet = nil; DispatchQueue.main.async { saveCalendar() } }.buttonStyle(.borderedProminent).keyboardShortcut(.defaultAction) } }
        }.fixedSize(horizontal: false, vertical: true)
    }
    private func saveCalendar() {
        do {
            let selectedSessions = calendarSelection ?? planner.sessions
            let count = try CalendarConnection.shared.saveSessions(selectedSessions)
            if Set(planner.sessions.map(\.id)).isSubset(of: Set(selectedSessions.map(\.id))) {
                planner.savedToCalendar = true
            }
            planner.persistPlan()
            planner.messages.append(Message(text: count == 0 ? "These events are already on your calendar." : "Added \(count) events to your calendar. You can edit them in Calendar.", isUser: false))
        } catch { let alert = NSAlert(error: error); alert.runModal() }
    }
}
