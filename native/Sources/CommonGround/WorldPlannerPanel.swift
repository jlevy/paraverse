import SwiftUI

struct WorldPlannerPanel: View {
    @Bindable var planner: Planner
    @Binding var showPlan: Bool
    @State private var browsing = false
    @State private var search = ""
    private static let catalog = (try? JSONDecoder().decode([String: [PlannedSession]].self, from: Data(contentsOf: worldAsset("browse-events.json")))) ?? [:]
    @State private var section: PlanSection = .sessions
    private enum PlanSection: String, CaseIterable {
        case sessions = "Speaker sessions", attendees = "Attendees", external = "External events"
    }
    private var speakerSessions: [PlannedSession] {
        planner.sessions.filter { session in !planner.sideEvents.contains { $0.id == session.id } }
    }
    private var recommendedCount: Int {
        speakerSessions.count + planner.peopleToMeet.count + planner.sideEvents.count
    }
    private var catalogCount: Int {
        (Self.catalog["sessions"] ?? []).count + WorldSpeaker.directoryPeople.count + (Self.catalog["external"] ?? []).count
    }
    private func filtered(_ sessions: [PlannedSession]) -> [PlannedSession] {
        guard browsing && !search.isEmpty else { return sessions }
        return sessions.filter { "\($0.title) \($0.speakers) \($0.about ?? "")".localizedCaseInsensitiveContains(search) }
    }
    private var visibleSessions: [PlannedSession] { filtered(browsing ? Self.catalog["sessions"] ?? [] : speakerSessions) }
    private var visibleEvents: [PlannedSession] { filtered(browsing ? Self.catalog["external"] ?? [] : planner.sideEvents) }
    private var visiblePeople: [WorldSpeaker] {
        WorldSpeaker.directoryPeople.filter {
            search.isEmpty || "\($0.name) \($0.role) \($0.company) \($0.biography)".localizedCaseInsensitiveContains(search)
        }
    }
    var close: () -> Void
    var saveCalendar: ([PlannedSession]) -> Void
    var openSpeaker: (WorldSpeaker) -> Void
    var body: some View {
        WorldPlaque {
            if planner.generatingRecommendations {
                RecommendationLoadingView(status: planner.status, close: close)
            } else {
            VStack(spacing: 20) {
                HStack {
                    VStack(alignment:.leading,spacing:4) {
                        Text(showPlan ? (browsing ? "Explore the conference" : "Recommendations for you") : "Ask your guide")
                            .font(.system(size: 22, weight: .bold, design: .monospaced))
                        Text("GitHub Universe · Oct 28–29")
                            .font(.system(size: 12)).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Button(showPlan ? "Chat" : "Recommendations") { showPlan.toggle() }
                        .buttonStyle(PlannerQuietButtonStyle())
                    Button(action:close) {Image(systemName:"xmark")}.buttonStyle(PlannerQuietButtonStyle()).accessibilityLabel("Close companion").help("Close")
                }
                if showPlan {
                HStack(spacing: 24) {
                    Button("Recommended · \(recommendedCount)") { browsing = false; search = "" }
                        .buttonStyle(PlannerTabStyle(selected: !browsing))
                        .accessibilityAddTraits(!browsing ? .isSelected : [])
                    Button("All · \(catalogCount)") { browsing = true; search = "" }
                        .buttonStyle(PlannerTabStyle(selected: browsing))
                        .accessibilityAddTraits(browsing ? .isSelected : [])
                    Spacer(minLength: 0)
                }
                .accessibilityElement(children: .contain)
                .accessibilityLabel("Recommendation scope, counts across all categories")
                .overlay(alignment: .bottom) { Rectangle().fill(.white.opacity(0.1)).frame(height: 1) }
                HStack(spacing: 16) {
                    ForEach(PlanSection.allCases, id: \.self) { tab in
                        Button(tab.rawValue) { section = tab; search = "" }
                            .buttonStyle(PlannerTabStyle(selected: showPlan && section == tab))
                            .accessibilityAddTraits(showPlan && section == tab ? .isSelected : [])
                    }
                    Spacer(minLength: 0)
                }
                .overlay(alignment: .bottom) { Rectangle().fill(.white.opacity(0.1)).frame(height: 1) }
                }
                if showPlan { itinerary } else { conversation }
            }
            .padding(10)
            .foregroundStyle(Color(red:0.96,green:0.91,blue:0.80))
            }
        }
        .onAppear { if planner.showPlan {showPlan=true;planner.showPlan=false} }
        .onExitCommand(perform:close)
        .onChange(of:planner.showPlan) { _, shown in if shown {section = .sessions;browsing=false;search="";showPlan=true;planner.showPlan=false} }
    }
    private var chatMessages: ArraySlice<Message> {
        guard let firstQuestion = planner.messages.firstIndex(where: \.isUser) else { return [] }
        return planner.messages[firstQuestion...]
    }

    private var chatWelcome: some View {
        VStack(alignment: .leading, spacing: 16) {
            PixelPlanet().frame(width: 44, height: 44).accessibilityHidden(true)
            Text("How can I help you today?")
                .font(.system(size: 20, weight: .semibold))
                .foregroundStyle(Brand.welcomeTitle)
            VStack(alignment: .leading, spacing: 0) {
                Button {
                    planner.send("Help me create a coffee meetup on Luma after my sessions for people who share my interests.")
                } label: { chatSuggestion("Create a meetup on Luma", icon: "plus.bubble") }
                Button {
                    planner.send("Who should I meet at GitHub Universe based on my interests?")
                } label: { chatSuggestion("Find people with shared interests", icon: "person.2") }
                Button {
                    planner.send("Which sessions and speakers would you recommend for my interests, and why?")
                } label: { chatSuggestion("Explore sessions and speakers", icon: "text.bubble") }
                Button {
                    planner.prompt = "Help me adjust my schedule. "
                } label: { chatSuggestion("Adjust my schedule", icon: "calendar") }
            }
            .buttonStyle(ChatSuggestionStyle())
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.bottom, 8)
        .disabled(planner.busy)
    }

    private func chatSuggestion(_ title: String, icon: String) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon).frame(width: 20, alignment: .center)
            Text(title)
            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var conversation:some View {
        VStack(spacing:12) {
            if chatMessages.isEmpty {
                chatWelcome
            } else {
            GeometryReader { geometry in
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment:.leading,spacing:18) {
                        ForEach(chatMessages) { message in
                            VStack(alignment:.leading,spacing:10) {
                                Text(message.isUser ? "YOU" : "UNIVERSE GUIDE").font(.system(size:10,weight:.bold,design:.monospaced)).foregroundStyle(message.isUser ? Color.cyan : Color(red:0.80,green:0.69,blue:0.98))
                                Text(.init(message.text)).font(.system(size:14)).lineSpacing(4).textSelection(.enabled).frame(maxWidth:.infinity,alignment:.leading)
                                if let card = message.meetupCard { card }
                                ForEach(message.recommendations) { person in MeetPersonCard(person:person,gameStyle:true) }
                                ForEach(message.eventSessions) { session in recommendationCard(session) }
                                if message.hasPlan { Button("View recommendations") {browsing=false;search="";showPlan=true}.buttonStyle(WorldButtonStyle(teal:true)) }
                            }.padding(14).background(PixelPanel().fill(message.isUser ? Color.teal.opacity(0.14) : Color.white.opacity(0.045)))
                        }
                        if planner.busy { ThinkingStatus(text: planner.status) }
                        Color.clear.frame(height:1).id("bottom")
                    }.padding(.vertical,4)
                        .frame(minHeight: geometry.size.height, alignment: .topLeading)
                }.onChange(of:planner.messages.count) {_,_ in proxy.scrollTo("bottom",anchor:.bottom)}
                    .onChange(of:planner.busy) {_,_ in proxy.scrollTo("bottom",anchor:.bottom)}
            }
            }
            }
            HStack(alignment:.center,spacing:8) {
                TextField("Ask your guide…",text:$planner.prompt,axis:.vertical)
                    .textFieldStyle(.plain).lineLimit(1...6).font(.system(size:14))
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .onSubmit {planner.send()}.accessibilityLabel("Message your conference companion")
                Button {planner.send()} label:{Image(systemName:"arrow.up")}
                    .buttonStyle(PlannerQuietButtonStyle()).disabled(planner.busy || planner.prompt.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty)
                    .accessibilityLabel("Send message")
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 4)
            .background(PixelPanel().fill(Color.black.opacity(0.22)))
            .overlay(PixelPanel().stroke(Brand.fieldBorder, lineWidth: 1))
        }
        .frame(maxHeight: .infinity, alignment: .bottom)
    }
    private var itinerary:some View {
        ScrollView {
            LazyVStack(alignment:.leading,spacing:16) {
                ForEach(planner.recommendationWarnings.filter { warning in
                    !browsing && ((section == .attendees && warning.hasPrefix("People")) ||
                    (section == .external && (warning.hasPrefix("External") || warning.hasPrefix("Side events"))))
                }, id: \.self) { warning in
                    HStack {
                        Text(warning).font(.system(size: 13)).foregroundStyle(Brand.welcomeSubtitle)
                        Spacer()
                        Button("Try again") {
                            if section == .attendees { planner.refreshPeople() }
                            else { planner.refreshExternalEvents() }
                        }.buttonStyle(PlannerQuietButtonStyle()).disabled(planner.busy)
                    }
                }
                if browsing {
                    TextField(section == .attendees ? "Search people, roles, or interests" : "Search by title, speaker, or topic", text: $search)
                        .textFieldStyle(.roundedBorder)
                        .accessibilityLabel("Search catalog")
                    if section == .attendees ? visiblePeople.isEmpty : (section == .sessions ? visibleSessions : visibleEvents).isEmpty {
                        Text("No matches. Try another search.").foregroundStyle(.secondary)
                    }
                }
                if section == .sessions {
                if !browsing && speakerSessions.isEmpty {
                    Text("A good day starts with what matters to you. Tell the guide what you want to learn or who you want to meet.").lineSpacing(4)
                    Button("Ask your guide") {showPlan=false}.buttonStyle(WorldButtonStyle(teal:true))
                }
                ForEach(Array(Set(visibleSessions.map(\.day))).sorted(),id:\.self) {day in
                    Text(dayHeading(day)).font(.system(size:13,weight:.bold,design:.monospaced)).foregroundStyle(.cyan)
                    ForEach(visibleSessions.filter{$0.day==day}.sorted{$0.start<$1.start}) {session in
                        recommendationCard(session)
                    }
                }
                }
                if section == .attendees {
                    if browsing {
                        ForEach(visiblePeople) { person in
                            Button { openSpeaker(person) } label: {
                                HStack(spacing: 12) {
                                    if let sprite = WorldCharacter.recommendationImage(for: person.id) {
                                        Image(nsImage: sprite).resizable().interpolation(.none).scaledToFit().frame(width: 44, height: 52)
                                    }
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(person.name).font(.headline)
                                        Text([person.role, person.company].filter { !$0.isEmpty }.joined(separator: " · "))
                                            .font(.caption).foregroundStyle(Brand.welcomeSubtitle)
                                    }
                                    Spacer()
                                    Image(systemName: "chevron.right")
                                }.frame(maxWidth: .infinity, alignment: .leading)
                            }.buttonStyle(PlannerQuietButtonStyle())
                        }
                    } else {
                    if planner.peopleToMeet.isEmpty {
                        Text("No attendee recommendations yet.").foregroundStyle(.secondary)
                        Button("Find people to meet") { planner.send("Who should I meet based on my interests?"); showPlan = false }
                            .buttonStyle(WorldButtonStyle()).disabled(planner.busy)
                    }
                    ForEach(planner.peopleToMeet) { person in MeetPersonCard(person: person, gameStyle: true) }
                    }
                }
                if section == .external {
                    if !browsing && planner.sideEvents.isEmpty {
                        Button("Find external events") {planner.send("Suggest external events that fit my profile and session plan");showPlan=false}.buttonStyle(WorldButtonStyle()).disabled(planner.busy)
                    } else {
                        ForEach(Array(Set(visibleEvents.map(\.day))).sorted(), id: \.self) { day in
                            Text(dayHeading(day)).font(.system(size: 13, weight: .bold, design: .monospaced)).foregroundStyle(.cyan)
                            ForEach(visibleEvents.filter { $0.day == day }.sorted { $0.start < $1.start }) { event in
                                recommendationCard(event)
                            }
                        }
                    }
                }
                if !browsing && section != .attendees {
                    HStack {
                        Spacer()
                        let events = section == .sessions ? speakerSessions : planner.sideEvents
                        if !events.isEmpty {
                            Button("Add all to calendar") { saveCalendar(events) }
                                .buttonStyle(WorldButtonStyle(teal: true))
                        }
                    }
                    .padding(.top, 8)
                }
            }.font(.system(size:14)).padding(.vertical,4)
                .id("\(browsing)-\(section.rawValue)")
        }
    }
    private func recommendationCard(_ session: PlannedSession) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            RecommendationReason(reason: session.reason)
        VStack(alignment: .leading, spacing: 16) {
            sessionDetails(session)
            HStack(alignment: .center, spacing: 12) {
                Spacer(minLength: 0)
                Button("Add to calendar") { saveCalendar([session]) }
                    .buttonStyle(PlannerQuietButtonStyle())
            }
        }
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(PixelPanel().fill(Color(red: 0.12, green: 0.15, blue: 0.19)))
        .overlay(PixelPanel().stroke(Brand.fieldBorder, lineWidth: 1))
        }
        .padding(.bottom, 8)
    }

    private func dayHeading(_ day: String) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyy-MM-dd"
        guard let date = formatter.date(from: day) else { return day }
        formatter.locale = .current
        formatter.setLocalizedDateFormatFromTemplate("EEEE MMMM d")
        return formatter.string(from: date)
    }

    private func linkedSpeakers(for session: PlannedSession) -> AttributedString {
        var text = AttributedString(session.speakers)
        for speaker in WorldSpeaker.all {
            guard let range = text.range(of: speaker.name, options: .caseInsensitive) else { continue }
            let matchesSession = speaker.sessions.contains { $0.id == session.id || $0.url == session.sourceURL }
            let uniqueName = WorldSpeaker.all.filter { $0.name.caseInsensitiveCompare(speaker.name) == .orderedSame }.count == 1
            guard matchesSession || uniqueName else { continue }
            var url = URLComponents()
            url.scheme = "paraverse-speaker"
            url.host = "profile"
            url.queryItems = [URLQueryItem(name: "id", value: speaker.id)]
            text[range].link = url.url
            text[range].underlineStyle = .single
        }
        return text
    }

    private func sessionDetails(_ session:PlannedSession)->some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 6) {
                Text(session.time)
                    .font(.system(size: 12, weight: .medium)).foregroundStyle(Brand.welcomeSubtitle)
                Group {
                    if let url = URL(string: session.sourceURL) {
                        Link(session.title, destination: url).buttonStyle(.plain)
                            .help("Open event details")
                    } else { Text(session.title) }
                }
                    .font(.system(size: 16, weight: .bold, design: .monospaced))
                    .foregroundStyle(Brand.welcomeTitle)
                    .fixedSize(horizontal: false, vertical: true)
                Text(linkedSpeakers(for: session))
                    .font(.system(size: 13)).foregroundStyle(Brand.welcomeSubtitle)
                    .tint(Brand.welcomeSubtitle)
                    .environment(\.openURL, OpenURLAction { url in
                        guard url.scheme == "paraverse-speaker",
                              let id = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems?.first(where: { $0.name == "id" })?.value,
                              let speaker = WorldSpeaker.all.first(where: { $0.id == id }) else { return .systemAction }
                        openSpeaker(speaker)
                        return .handled
                    })
            }
            RecommendationContext(about: session.about)
        }
    }
}

private struct RecommendationLoadingView: View {
    let status: String
    let close: () -> Void
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    var body: some View {
        VStack(spacing: 24) {
            TimelineView(.animation(minimumInterval: 1.0 / 30, paused: reduceMotion)) { timeline in
                let wave = reduceMotion ? 0 : sin(timeline.date.timeIntervalSinceReferenceDate * .pi)
                PixelPlanet()
                    .frame(width: 120, height: 120)
                    .scaleEffect(1 + wave * 0.035)
                    .offset(y: wave * 6)
                    .frame(width: 144, height: 160)
                    .accessibilityHidden(true)
            }
            Text("Generating your recommendations…")
                .font(.system(size: 22, weight: .bold, design: .monospaced))
                .multilineTextAlignment(.center)
            ThinkingStatus(text: status)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
        .overlay(alignment: .topTrailing) {
            Button(action: close) { Image(systemName: "xmark") }
                .buttonStyle(PlannerQuietButtonStyle()).accessibilityLabel("Close companion")
        }
        .padding(16)
        .foregroundStyle(Color(red: 0.96, green: 0.91, blue: 0.80))
    }
}

private struct PlannerTabStyle: ButtonStyle {
    let selected: Bool
    @Environment(\.isEnabled) private var isEnabled
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 13, weight: selected ? .semibold : .medium))
            .foregroundStyle(selected ? Brand.welcomeTitle : Brand.welcomeSubtitle)
            .frame(minHeight: 44)
            .background(Color.white.opacity(configuration.isPressed ? 0.08 : 0))
            .overlay(alignment: .bottom) {
                Rectangle().fill(selected ? Brand.buttonBorder : .clear).frame(height: 3)
            }
            .contentShape(Rectangle())
            .onChange(of: configuration.isPressed) { _, pressed in
                if pressed && isEnabled { InterfaceSounds.play(primary: false) }
            }
    }
}

struct PlannerQuietButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 13, weight: .medium))
            .foregroundStyle(Brand.welcomeSubtitle)
            .padding(.horizontal, 12)
            .frame(minWidth: 44, minHeight: 44)
            .background(PixelPanel().fill(.white.opacity(configuration.isPressed ? 0.1 : 0)))
            .contentShape(Rectangle())
            .opacity(isEnabled ? 1 : 0.45)
            .onChange(of: configuration.isPressed) { _, pressed in
                if pressed && isEnabled { InterfaceSounds.play(primary: false) }
            }
    }
}

private struct ChatSuggestionStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 14))
            .foregroundStyle(Brand.welcomeSubtitle)
            .frame(minHeight: 44)
            .background(PixelPanel().fill(.white.opacity(configuration.isPressed ? 0.08 : 0)))
            .contentShape(Rectangle())
            .opacity(isEnabled ? 1 : 0.45)
            .onChange(of: configuration.isPressed) { _, pressed in
                if pressed && isEnabled { InterfaceSounds.play(primary: false) }
            }
    }
}

private struct ThinkingStatus: View {
    let text: String
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        Text(text)
            .font(.system(size: 14))
            .foregroundStyle(Brand.welcomeSubtitle.opacity(0.7))
            .overlay {
                if !reduceMotion {
                    TimelineView(.animation(minimumInterval: 1.0 / 30)) { timeline in
                        GeometryReader { geometry in
                            let phase = timeline.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 2.4) / 2.4
                            LinearGradient(colors: [.clear, Brand.welcomeTitle.opacity(0.9), .clear], startPoint: .leading, endPoint: .trailing)
                                .frame(width: geometry.size.width * 0.45)
                                .offset(x: geometry.size.width * (phase * 1.45 - 0.45))
                        }
                    }
                    .mask(Text(text).font(.system(size: 14)))
                    .accessibilityHidden(true)
                    .allowsHitTesting(false)
                }
            }
    }
}
