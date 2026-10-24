import SwiftUI

struct YourProfileView: View {
    let profile: AttendeeProfile
    let save: (AttendeeProfile) -> Void
    @State private var draft = AttendeeProfile()
    @State private var interest = ""
    @State private var category = "personal"
    @State private var busy = false
    @State private var note: String?
    @State private var refreshTask: Task<Void, Never>?
    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 16) {
                ProfileAvatar(profile: draft, size: 56)
                VStack(alignment: .leading, spacing: 5) {
                    Text(draft.name.isEmpty ? "Your profile" : draft.name).font(.system(size: 28, weight: .medium, design: .serif))
                    Text("A little about you. A better starting point for your plans.").foregroundStyle(.secondary)
                }
                Spacer()
                Button("Save changes") { save(draft); note = "Profile saved. Conference recommendations will use your updated interests." }
                    .buttonStyle(.borderedProminent).tint(Brand.primaryAction).disabled(!draft.isValid || busy || draft == profile)
            }.padding(28)
            Form {
                Section("About you") {
                    TextField("Name", text: $draft.name)
                    TextField("Title", text: Binding(get: { draft.title ?? "" }, set: { draft.title = $0 }))
                    TextField("Background", text: $draft.background, axis: .vertical).lineLimit(3...6)
                    TextField("Based in", text: $draft.city)
                    Picker("Travel", selection: $draft.travel) {
                        ForEach(["Nearby", "Open to travel", "Online"], id: \.self) { Text($0) }
                    }
                }
                interestSection("Professional interests", personal: false)
                interestSection("Personal interests", personal: true)
                Section("Add an interest") {
                    TextField("Interest", text: $interest, prompt: Text("For example, live music or basketball"))
                    Picker("Category", selection: $category) { Text("Personal").tag("personal"); Text("Professional").tag("professional") }
                    Button("Add interest") {
                        let value = interest.trimmingCharacters(in: .whitespacesAndNewlines)
                        InterestSelection.add(value, to: &draft.interests)
                        if category == "personal" { if draft.personalInterests == nil { draft.personalInterests = [] }; draft.personalInterests?.insert(value) }
                        interest = ""
                    }.disabled(interest.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || interest.count > 60)
                }
                Section("Public profiles") {
                    TextField("LinkedIn", text: Binding(get: { draft.linkedInURL ?? "" }, set: { draft.linkedInURL = $0 }))
                    TextField("X", text: Binding(get: { draft.xURL ?? "" }, set: { draft.xURL = $0 }))
                    TextField("GitHub (optional)", text: Binding(get: { draft.githubURL ?? "" }, set: { draft.githubURL = $0.trimmingCharacters(in: .whitespacesAndNewlines) }))
                    Text("Generate a background and suggested interests from public information. Review the results before saving.").font(.caption).foregroundStyle(.secondary)
                    HStack {
                        Button("Generate from profiles") { generate() }.disabled(busy || !draft.socialLinksValid || ((draft.linkedInURL ?? "").isEmpty && (draft.xURL ?? "").isEmpty && (draft.githubURL ?? "").isEmpty))
                        if busy { ProgressView().controlSize(.small); Text("Reading profiles…").foregroundStyle(.secondary) }
                    }
                }
                if let note { Section { Text(note).foregroundStyle(.secondary) } }
            }.formStyle(.grouped).disabled(busy)
        }.background(Brand.paper)
        .onAppear { draft = profile }
        .onDisappear { refreshTask?.cancel() }
    }
    private func interestSection(_ title: String, personal: Bool) -> some View {
        Section(title) {
            let values = draft.interests.sorted().filter { (draft.personalInterests?.contains($0) ?? false) == personal }
            if values.isEmpty { Text(personal ? "Add what you enjoy outside work. Suggestions appear here when your public posts support them." : "Add the topics you work on or want to explore.").foregroundStyle(.secondary) }
            ForEach(values, id: \.self) { value in
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text(value)
                        Spacer()
                        Menu { Button(personal ? "Move to professional" : "Move to personal") {
                            if personal { draft.personalInterests?.remove(value) }
                            else { if draft.personalInterests == nil { draft.personalInterests = [] }; draft.personalInterests?.insert(value) }
                        }; Button("Remove", role: .destructive) { draft.interests.remove(value); draft.personalInterests?.remove(value) } } label: { Image(systemName: "ellipsis") }.menuStyle(.borderlessButton).fixedSize().accessibilityLabel("Edit \(value)")
                    }
                    if let suggestion = draft.interestSuggestions?.first(where: { $0.label == value }) {
                        DisclosureGroup("From your profiles") {
                            Text(suggestion.reason).foregroundStyle(.secondary)
                            ForEach(suggestion.evidence ?? [], id: \.sourceURL) { evidence in
                                Text("“\(evidence.quote)”").font(.caption)
                                Link("View original", destination: evidence.sourceURL).font(.caption)
                            }
                        }.font(.caption)
                    }
                }
            }
        }
    }
    private func generate() {
        busy = true; note = nil
        refreshTask = Task {
            do {
                let result = try await ProfileImportClient().read(linkedIn: draft.linkedInURL, x: draft.xURL, github: draft.githubURL)
                try Task.checkCancellation()
                draft.title = result.title; draft.background = result.background; draft.avatarURL = result.avatarURL
                draft.interestSuggestions = result.interests
                for item in result.interests {
                    InterestSelection.add(item.label, to: &draft.interests)
                    if item.category == "personal" { if draft.personalInterests == nil { draft.personalInterests = [] }; draft.personalInterests?.insert(item.label) }
                }
                note = "Suggestions ready. Review your profile, then save changes."
            } catch { if !Task.isCancelled { note = error.localizedDescription } }
            busy = false
        }
    }
}
