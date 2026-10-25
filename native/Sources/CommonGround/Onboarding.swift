import SwiftUI

struct AttendeeProfile: Codable, Equatable {
    var name = ""
    var background = ""
    var title: String?
    var city = ""
    var linkedInURL: String?
    var xURL: String?
    var githubURL: String?
    var avatarURL: String?
    var travel = "Nearby"
    var interests: Set<String> = []
    var conferences: Set<String> = []
    var conferenceStates: [String: ConferenceStatus]?
    var groupMatchingIDs: Set<String>?
    var interestSuggestions: [InterestSuggestion]?
    var personalInterests: Set<String>?
    var initials: String { name.split(separator: " ").prefix(2).compactMap(\.first).map(String.init).joined().uppercased() }
    static func validSocialURL(_ value: String?, hosts: Set<String>, profilePrefix: String? = nil) -> Bool {
        guard let value, !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return true }
        guard let url = URL(string: value), url.scheme == "https", let host = url.host?.lowercased(), hosts.contains(host), url.user == nil, url.password == nil else { return false }
        let parts = url.path.split(separator: "/")
        if let profilePrefix { return parts.count >= 2 && parts.first == Substring(profilePrefix) }
        return !parts.isEmpty
    }
    static func validGitHubURL(_ value: String?) -> Bool {
        guard let value, !value.isEmpty else { return true }
        let normalized = value.hasPrefix("github.com/") ? "https://" + value : value
        guard let url = URL(string: normalized), url.scheme == "https",
              ["github.com", "www.github.com"].contains(url.host ?? ""),
              url.user == nil, url.password == nil, url.port == nil, url.query == nil, url.fragment == nil else { return false }
        let handle = url.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        return handle.range(of: "^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$", options: .regularExpression) != nil
            && !["settings", "login", "signup", "explore", "topics", "marketplace", "orgs", "search", "features", "pricing", "about"].contains(handle.lowercased())
    }
    var socialLinksValid: Bool {
        Self.validGitHubURL(githubURL) && Self.validSocialURL(linkedInURL, hosts: ["linkedin.com", "www.linkedin.com"], profilePrefix: "in") && Self.validSocialURL(xURL, hosts: ["x.com", "www.x.com", "twitter.com", "www.twitter.com"])
    }
    var hasRequiredSocialProfiles: Bool {
        guard let linkedInURL, let xURL,
              !linkedInURL.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              !xURL.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              socialLinksValid,
              let x = URL(string: xURL), x.path.split(separator: "/").count == 1 else { return false }
        let handle = String(x.path.dropFirst()).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        return handle.range(of: "^[A-Za-z0-9_]{1,15}$", options: .regularExpression) != nil
            && !["home", "explore", "search", "settings", "notifications", "messages", "i", "intent", "login", "signup"].contains(handle.lowercased())
    }
    var isValid: Bool { !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !city.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !interests.isEmpty && socialLinksValid }
}

@MainActor @Observable final class ProfileStore {
    var profile: AttendeeProfile
    var stage: Int
    var editing = false
    private let defaults: UserDefaults
    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        if let data = defaults.data(forKey: "attendeeProfile"), let saved = try? JSONDecoder().decode(AttendeeProfile.self, from: data), saved.isValid {
            profile = saved; stage = 4
        } else {
            profile = defaults.data(forKey: "onboardingDraft").flatMap { try? JSONDecoder().decode(AttendeeProfile.self, from: $0) } ?? AttendeeProfile()
            stage = 0
        }
        // Recover drafts damaged by the old clear-before-import flow, using only the same person's saved workspace.
        if profile.background.isEmpty, profile.interests.isEmpty,
           !(profile.interestSuggestions ?? []).isEmpty,
           let snapshot = defaults.dictionary(forKey: "previousWorkspace"),
           let data = snapshot["attendeeProfile"] as? Data,
           let saved = try? JSONDecoder().decode(AttendeeProfile.self, from: data),
           saved.name == profile.name, saved.linkedInURL == profile.linkedInURL,
           saved.xURL == profile.xURL, saved.githubURL == profile.githubURL {
            profile.background = saved.background
            profile.title = saved.title
            profile.interests = saved.interests
            profile.interestSuggestions = saved.interestSuggestions
            profile.personalInterests = saved.personalInterests
            defaults.set(try? JSONEncoder().encode(profile), forKey: "onboardingDraft")
        }
    }
    private let workspaceKeys = ["attendeeProfile", "sessionPlanProfile", "lastSessionPlan", "lastSideEvents", "lastPlanPeople", "sessionPlanSaved"]
    var canRestorePrevious: Bool { defaults.dictionary(forKey: "previousWorkspace") != nil }
    func startNewProfile() {
        if profile.isValid {
            var snapshot: [String: Any] = [:]
            for key in workspaceKeys { snapshot[key] = defaults.object(forKey: key) }
            defaults.set(snapshot, forKey: "previousWorkspace")
        }
        for key in workspaceKeys { defaults.removeObject(forKey: key) }
        defaults.removeObject(forKey: "onboardingDraft")
        profile = AttendeeProfile(); editing = false; stage = 1
    }
    func saveDraft(_ value: AttendeeProfile) {
        profile = value
        defaults.set(try? JSONEncoder().encode(value), forKey: "onboardingDraft")
    }
    func logOut() {
        for key in workspaceKeys + ["onboardingDraft", "previousWorkspace"] {
            defaults.removeObject(forKey: key)
        }
        profile = AttendeeProfile(); editing = false; stage = 0
    }
    func restorePrevious() {
        guard let snapshot = defaults.dictionary(forKey: "previousWorkspace"),
              let data = snapshot["attendeeProfile"] as? Data,
              let saved = try? JSONDecoder().decode(AttendeeProfile.self, from: data) else { return }
        var current: [String: Any] = [:]
        if profile.isValid { for key in workspaceKeys { current[key] = defaults.object(forKey: key) } }
        for key in workspaceKeys { defaults.removeObject(forKey: key); if let value = snapshot[key] { defaults.set(value, forKey: key) } }
        if current.isEmpty { defaults.removeObject(forKey: "previousWorkspace") } else { defaults.set(current, forKey: "previousWorkspace") }
        profile = saved; editing = false; stage = 4
    }
    func save(_ value: AttendeeProfile) {
        saveDraft(value)
        defaults.set(try? JSONEncoder().encode(value), forKey: "attendeeProfile")
        editing = false; stage = 4
    }
}

struct AppRoot: View {
    @Bindable var store: ProfileStore
    @Bindable var planner: Planner
    @State private var landingMotion = true
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    var body: some View {
        Group {
            if store.stage == 4 {
                ContentView(planner: planner, profile: store.profile, logOut: { store.logOut(); planner.reset(); planner.messages = [] }, editProfile: { store.editing = true }, saveProfile: { store.save($0) })
            } else if store.stage == 0 {
                VStack(spacing: 0) {
                    HStack(alignment: .center, spacing: 16) {
                        LandingPlanet(animated: landingMotion)
                            .frame(width: 80, height: 80)
                            .accessibilityHidden(true)
                        Text("Paraverse")
                            .font(.system(size: 48, weight: .bold, design: .monospaced))
                            .tracking(-1.0)
                            .foregroundStyle(Brand.welcomeTitle)
                            .accessibilityAddTraits(.isHeader)
                    }
                    Text("Discover conferences worth your time\nand meet people who share your interests")
                        .font(.system(size: 18)).multilineTextAlignment(.center).lineSpacing(5)
                        .foregroundStyle(Brand.welcomeSubtitle)
                        .padding(.top, 24)
                    Button { store.stage = 1 } label: {
                        HStack(spacing: 8) {
                            Text("START").font(.system(size: 16, weight: .bold, design: .monospaced))
                            Image(systemName: "arrow.right").font(.system(size: 14, weight: .medium))
                        }.padding(.horizontal, 24).frame(height: 44)
                    }
                    .buttonStyle(WorldButtonStyle(teal: true))
                    .keyboardShortcut(.defaultAction)
                    .padding(.top, 24)
                }
                .padding(.horizontal, 32)
                .padding(.bottom, 180)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background { WelcomeBackdrop(animated: landingMotion) }
                .overlay(alignment: .bottomTrailing) {
                    if !reduceMotion {
                        Button { landingMotion.toggle() } label: {
                            Image(systemName: landingMotion ? "pause.fill" : "play.fill")
                                .font(.system(size: 12))
                                .frame(width: 44, height: 44)
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(Brand.welcomeSubtitle)
                        .background(Brand.welcomeBackground.opacity(0.8))
                        .accessibilityLabel(landingMotion ? "Pause background animation" : "Play background animation")
                        .help(landingMotion ? "Pause background animation" : "Play background animation")
                        .padding(16)
                    }
                }
            } else {
                ProfileFlow(initial: store.profile, onDraftChange: { store.saveDraft($0) }, onCancel: { store.stage = 0 }) { value in
                    store.save(value)
                    planner.start(for: value)
                }
            }
        }
        .modifier(FlowTransition(step: store.stage))
        .background(Brand.welcomeBackground)
        .onAppear { if store.stage == 4 { planner.start(for: store.profile) } }
        .sheet(isPresented: $store.editing) {
            VStack {
                HStack { Spacer(); Button("Done") { store.editing = false } }.padding([.top, .horizontal])
                YourProfileView(profile: store.profile) { store.save($0) }
            }.frame(width: 740, height: 720)
        }
    }
}

struct ProfileFlow: View {
    @State private var draft: AttendeeProfile
    @State private var step = 0
    @State private var importing = false
    @State private var importNote: String?
    @State private var suggestions: [InterestSuggestion] = []
    @State private var customInterest = ""
    @State private var editingBackground = false
    @State private var preparationError: String?
    @State private var preparationAttempt = 0
    @State private var importTask: Task<Void, Never>?
    private let importer: any ProfileImporting
    private let originalProfile: AttendeeProfile
    let onDraftChange: (AttendeeProfile) -> Void
    let onCancel: () -> Void
    let onFinish: (AttendeeProfile) -> Void
    private let topics = ["Design tools", "AI & machine learning", "Software development", "Product design", "Startups", "Open source"]
    init(initial: AttendeeProfile, importer: any ProfileImporting = ProfileImportClient(), onDraftChange: @escaping (AttendeeProfile) -> Void = { _ in }, onCancel: @escaping () -> Void, onFinish: @escaping (AttendeeProfile) -> Void) {
        originalProfile = initial; _draft = State(initialValue: initial); _suggestions = State(initialValue: initial.interestSuggestions ?? []); self.importer = importer; self.onDraftChange = onDraftChange; self.onCancel = onCancel; self.onFinish = onFinish
    }
    private var canContinue: Bool {
        step == 0 ? !draft.name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !draft.city.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && draft.hasRequiredSocialProfiles : !draft.interests.isEmpty
    }
    var body: some View {
        Group {
        if step == 2 { preparationView } else {
        WorldPlaque {
        VStack(alignment: .leading, spacing: 24) {
            HStack {
                if step == 0 {
                    PixelPlanet().frame(width:28,height:28)
                }
                Spacer()
                HStack(spacing: 8) {
                    Text("01  ABOUT YOU")
                        .foregroundStyle(step == 0 ? Color.primary : Color.secondary)
                    Image(systemName: "chevron.right").font(.system(size: 9, weight: .semibold))
                    Text("02  PROFILE").foregroundStyle(step == 1 ? Color.primary : Color.secondary)
                }.font(.system(size: 11, weight: .bold, design: .monospaced)).foregroundStyle(.secondary)
            }
            HStack(spacing: 20) {
                if step == 1 {
                    ProfileCharacter(profile: draft)
                }
                VStack(alignment: .leading, spacing: 8) {
                    if step == 0 {
                        Text("ABOUT YOU")
                            .font(.system(size: 30, weight: .medium, design: .monospaced))
                        Text("Find conferences and people for you.").foregroundStyle(.secondary)
                    } else {
                        Text(draft.name)
                            .font(.system(size: 28, weight: .medium, design: .monospaced))
                            .fixedSize(horizontal: false, vertical: true)
                        if !draft.city.isEmpty {
                            Text(draft.city.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() == "san francisco" ? "San Francisco, CA" : draft.city)
                                .font(.system(size: 13))
                                .foregroundStyle(.secondary)
                        }
                    }
                }
                Spacer(minLength: 0)
            }
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 24) {
                if step == 0 {
                    VStack(alignment: .leading, spacing: 26) {
                        HStack(alignment: .top, spacing: 18) {
                            profileField("Name", placeholder: "Full name", text: $draft.name)
                            CityField(city: $draft.city)
                        }.zIndex(1)
                        Divider()
                        VStack(alignment: .leading, spacing: 16) {
                            Text("Public profiles")
                                .font(.system(size: 16, weight: .semibold))
                            profileField("LinkedIn", placeholder: "https://linkedin.com/in/your-name", text: Binding(get: { draft.linkedInURL ?? "" }, set: { draft.linkedInURL = $0.trimmingCharacters(in: .whitespacesAndNewlines) }))
                            profileField("X", placeholder: "https://x.com/your-handle", text: Binding(get: { draft.xURL ?? "" }, set: { draft.xURL = $0.trimmingCharacters(in: .whitespacesAndNewlines) }))
                            profileField("GitHub (optional)", placeholder: "https://github.com/your-name", text: Binding(get: { draft.githubURL ?? "" }, set: { draft.githubURL = $0.trimmingCharacters(in: .whitespacesAndNewlines) }))
                            if !draft.socialLinksValid {
                                Label("Enter a valid public profile link.", systemImage: "exclamationmark.circle")
                                    .font(.caption).foregroundStyle(.red)
                            }
                        }
                    }.padding(.vertical, 8)
                } else if step == 1 {
                    VStack(alignment: .leading, spacing: 28) {
                        Group {
                            VStack(alignment: .leading, spacing: 12) {
                                HStack(alignment: .firstTextBaseline) {
                                    if draft.background.isEmpty && (draft.title ?? "").isEmpty {
                                        Text("Bio").font(.system(size: 17, weight: .medium))
                                    } else if !editingBackground, let title = draft.title, !title.isEmpty {
                                        Text(title).font(.system(size: 17, weight: .medium))
                                    }
                                    Spacer()
                                    Button(editingBackground ? "Done" : "Edit") { editingBackground.toggle() }
                                        .buttonStyle(.plain)
                                        .font(.system(size: 12, weight: .medium))
                                        .foregroundStyle(Brand.welcomeTitle)
                                        .padding(.horizontal, 10)
                                        .padding(.vertical, 6)
                                        .background(PixelPanel().fill(Brand.buttonSecondary))
                                        .overlay(PixelPanel().stroke(Brand.buttonBorder, lineWidth: 1))
                                        .accessibilityLabel(editingBackground ? "Finish editing background" : "Edit background")
                                }
                                if editingBackground || draft.background.isEmpty {
                                    profileField("Title", placeholder: "Role and company", text: Binding(get: { draft.title ?? "" }, set: { draft.title = $0 }))
                                    TextField("Background", text: $draft.background, axis: .vertical)
                                        .font(.system(size: 14)).lineSpacing(4)
                                        .lineLimit(3...6).textFieldStyle(.plain)
                                        .padding(12)
                                        .background(PixelPanel().fill(.black.opacity(0.25)))
                                        .overlay(PixelPanel().stroke(Color.teal.opacity(0.7),lineWidth:1))
                                } else {
                                    Text(draft.background).font(.system(size: 13)).lineSpacing(4)
                                        .foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                                }
                            }
                            Divider().padding(.vertical, 4)
                        }
                        ForEach(interestSections, id: \.self) { section in
                            let selectedTopics = topics(in: section).filter { draft.interests.contains($0) }
                            if !selectedTopics.isEmpty {
                                VStack(alignment: .leading, spacing: 6) {
                                    HStack {
                                        Text(section).font(.system(size: 16, weight: .semibold))
                                        Spacer()
                                    }
                                    .padding(.bottom, 4)
                                    VStack(spacing: 0) {
                                        ForEach(selectedTopics, id: \.self) { topic in
                                            InterestListRow(title: topic, actionTitle: "Remove", revealsOnHover: true) {
                                                draft.interests.remove(topic)
                                            }
                                            if topic != selectedTopics.last { Divider() }
                                        }
                                    }
                                }
                            }
                        }
                        HStack(spacing: 12) {
                            HStack(spacing: 8) {
                                PixelSearchIcon().fill(Brand.welcomeSubtitle).frame(width: 16, height: 16).accessibilityHidden(true)
                                TextField("Add an interest", text: $customInterest)
                                    .textFieldStyle(.plain)
                                    .accessibilityLabel("Add an interest")
                                    .onSubmit { addInterest() }
                            }
                            .font(.system(size: 13))
                            .padding(12)
                            .background(PixelPanel().fill(.black.opacity(0.2)))
                            .overlay(PixelPanel().stroke(Brand.fieldBorder, lineWidth: 1))
                            Button("ADD") { addInterest() }
                                .buttonStyle(WorldButtonStyle(teal: true))
                                .disabled(customInterest.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || customInterest.count > 60)
                        }
                    }.frame(maxWidth: .infinity, alignment: .leading).padding(.vertical, 8)
                } else {
                    ConferenceCards(profile: $draft)
                }
                }.padding(.bottom, 8)
            }
            if let importNote {
                Text(importNote).font(.callout).foregroundStyle(Brand.welcomeSubtitle)
                    .fixedSize(horizontal: false, vertical: true)
            }
            HStack {
                Button {
                    importTask?.cancel(); importing = false
                    if step == 0 { onCancel() } else { step -= 1 }
                } label: {
                    Label("Back", systemImage: "arrow.left")
                        .font(.system(size: 14, weight: .medium))
                        .frame(height: 44)
                        .contentShape(Rectangle())
                }.buttonStyle(WorldButtonStyle()).keyboardShortcut(.cancelAction)
                Spacer()
                if importing { ProgressView().controlSize(.small); Text("Reading profiles…").font(.caption) }
                Button {
                    if step == 0 { importProfile() }
                    else if step == 1 {
                        step = 2
                    } else { onFinish(draft) }
                } label: {
                    HStack(spacing: 10) {
                        Text(step == 1 ? "Find conferences" : "Generate profile")
                    }.font(.system(size: 15, weight: .semibold))
                        .frame(minWidth: 128, minHeight: 32)
                }.buttonStyle(WorldButtonStyle(teal:true))
                    .disabled(!canContinue || importing).keyboardShortcut(.defaultAction)
            }.padding(.top, 12)
                .overlay(alignment: .top) { Divider() }
        }.padding(20)
        }.frame(maxWidth: 700).padding(28)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background { WelcomeBackdrop().overlay(Color(red:0.06,green:0.08,blue:0.14).opacity(0.35)) }
        .environment(\.gameProfileFields, true)
        .preferredColorScheme(.dark)
        .foregroundStyle(Color(red:0.96,green:0.91,blue:0.80))
        .tint(.teal)
        }
        }
        .modifier(FlowTransition(step: step))
        .background(Brand.welcomeBackground)
        .onChange(of: draft) { _, value in onDraftChange(value) }
        .onDisappear { importTask?.cancel() }
    }
    private func profileField(_ title: String, placeholder: String, text: Binding<String>) -> some View {
        FloatingProfileField(title: title, placeholder: placeholder, text: text)
    }

    private var preparationView: some View {
        VStack(spacing: 20) {
            PixelPlanet().frame(width:52,height:52)
            Text("Finding conferences…").font(.system(size: 30, weight: .medium, design: .monospaced))
            if let preparationError {
                Text(preparationError).foregroundStyle(.secondary).multilineTextAlignment(.center)
                HStack {
                    Button("Back to profile") { step = 1 }
                    Button("Try again") { preparationAttempt += 1 }
                    Button("Open Discover") { onFinish(draft) }
                }
            } else {
                Text("Based on your interests and location.").foregroundStyle(.secondary)
                ProgressView().controlSize(.small)
                Button("Back to profile") { step = 1 }.buttonStyle(.plain).foregroundStyle(.secondary)
            }
        }.padding(40).frame(maxWidth: .infinity, maxHeight: .infinity).background { WelcomeBackdrop() }.preferredColorScheme(.dark).buttonStyle(WorldButtonStyle(teal:true))
        .task(id: preparationAttempt) {
            preparationError = nil
            SessionWarmup.prepare(draft)
            do {
                _ = try await ConferenceClient().search(ConferenceQuery(draft)) { _ in }
                try Task.checkCancellation()
                guard step == 2 else { return }
                onFinish(draft)
            } catch {
                if !Task.isCancelled { preparationError = "We couldn’t finish finding conferences. You can try again or explore Discover." }
            }
        }
    }
    private var hasLinks: Bool { !(draft.linkedInURL ?? "").isEmpty || !(draft.xURL ?? "").isEmpty }
    private var allTopics: [String] {
        var seen = Set<String>()
        return (suggestions.map(\.label) + draft.interests.sorted() + topics).filter { seen.insert($0.lowercased()).inserted }
    }
    private var interestSections: [String] {
        suggestions.isEmpty ? ["Selected"] : ["Work", "Personal", "Other interests"]
    }
    private func topics(in section: String) -> [String] {
        if section == "Selected" { return allTopics }
        if section == "Work" { return suggestions.filter { $0.category != "personal" }.map(\.label) }
        if section == "Personal" { return suggestions.filter { $0.category == "personal" }.map(\.label) }
        let generated = Set(suggestions.map { $0.label.lowercased() })
        return allTopics.filter { !generated.contains($0.lowercased()) }
    }
    private func addInterest() {
        InterestSelection.add(customInterest, to: &draft.interests)
        customInterest = ""
    }
    private func importProfile() {
        importNote = nil
        guard draft.hasRequiredSocialProfiles else { return }
        // Replaying onboarding should use the profile already reviewed, without a network dependency.
        if draft.name == originalProfile.name, draft.linkedInURL == originalProfile.linkedInURL,
           draft.xURL == originalProfile.xURL, draft.githubURL == originalProfile.githubURL,
           !draft.background.isEmpty && !draft.interests.isEmpty {
            step = 1
            return
        }
        importing = true
        importTask = Task {
            do {
                let updated = try await ProfileEnrichment.refresh(draft, using: importer)
                guard !Task.isCancelled else { return }
                draft = updated
                suggestions = updated.interestSuggestions ?? []
                step = 1
            } catch {
                guard !Task.isCancelled else { return }
                importNote = "We couldn’t load your profile. Your saved details are unchanged. Try Generate profile again."
            }
            importing = false
        }
    }

}


private struct WelcomeButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(.white)
            .background(Brand.primaryAction, in: Capsule())
            .opacity(configuration.isPressed ? 0.8 : 1)
            .contentShape(Capsule())
    }
}

private struct InterestListRow: View {
    let title: String
    let actionTitle: String
    let revealsOnHover: Bool
    let action: () -> Void
    @Environment(\.gameProfileFields) private var gameStyle
    @State private var hovered = false
    @FocusState private var actionFocused: Bool

    private var displayTitle: String {
        title.replacingOccurrences(of: #"\s*(?:[—–-]\s*historical|\(historical\))\s*$"#,
                                   with: "", options: [.regularExpression, .caseInsensitive])
    }
    var body: some View {
        HStack(spacing: 16) {
            if gameStyle { Text("◆").font(.system(size:10)).foregroundStyle(.teal) }
            Text(displayTitle)
                .font(.system(size: 14))
                .lineSpacing(3)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 8)
            Button(actionTitle, action: action)
                .buttonStyle(.plain)
                .font(.system(size: 12, weight: .medium))
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: true, vertical: true)
                .frame(minWidth: 56, minHeight: 28, alignment: .trailing)
                .padding(.trailing, 8)
                .layoutPriority(1)
                .focused($actionFocused)
                .opacity(!revealsOnHover || hovered || actionFocused ? 1 : 0)
                .accessibilityLabel("\(actionTitle) \(displayTitle)")
        }
        .padding(.vertical, 11)
        .frame(minHeight: 46)
        .padding(.horizontal, gameStyle ? 10 : 0)
        .background {
            if gameStyle { PixelPanel().fill(Color.teal.opacity(hovered ? 0.16 : 0.06)) }
            else { RoundedRectangle(cornerRadius:6).fill(hovered ? Color.primary.opacity(0.025) : Color.clear) }
        }
        .contentShape(Rectangle())
        .onHover { hovered = $0 }
    }
}
