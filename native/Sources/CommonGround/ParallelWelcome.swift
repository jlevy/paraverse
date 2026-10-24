import SwiftUI

/// A fictional parallel-self introduction; actions lead to real conference tools.
struct ParallelWelcome: View {
    let profile: AttendeeProfile
    let choose: (Destination) -> Void
    let dismiss: () -> Void
    enum Destination { case plan, people, sideEvents }
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var page = 0
    @State private var visibleCharacters = 0
    @State private var presented = false
    private static let entranceDuration = 0.22
    private static let characterDelay = Duration.milliseconds(24)
    private var firstName: String { profile.name.split(separator: " ").first.map(String.init) ?? "traveler" }
    private var lines: [String] { [
        "Hey \(firstName)... I’m you, but from a parallel universe.",
        "I’ve met everyone here and been to every session. Time works differently over here, haha.",
        "You can’t be in two sessions at once, but I can. Check back here for my summaries.",
        "I can help you find sessions you’ll love, interesting people to meet, and a few side quests. Want me to put a plan together?"
    ] }
    private var line: String { lines[page] }
    private var complete: Bool { visibleCharacters >= line.count }
    private var lastPage: Bool { page == lines.count - 1 }
    private var showingChoices: Bool { lastPage && complete }
    private var revealedLine: AttributedString {
        var text = AttributedString(line)
        let boundary = text.characters.index(text.startIndex, offsetBy: min(visibleCharacters, text.characters.count))
        text[boundary..<text.endIndex].foregroundColor = .clear
        return text
    }

    var body: some View {
        GeometryReader { viewport in
            ZStack(alignment: .bottom) {
                LinearGradient(colors: [.black.opacity(0.08), .black.opacity(0.12), .black.opacity(0.4)], startPoint: .top, endPoint: .bottom)
                    .ignoresSafeArea()
                    .allowsHitTesting(false)
                    .opacity(presented ? 1 : 0)
                WorldPlaque {
                    HStack(alignment: .top, spacing: 24) {
                        VStack(alignment: .leading, spacing: 10) {
                            ProfileCharacter(profile: profile, size: viewport.size.width < 640 ? 64 : 104)
                        }
                        VStack(alignment: .leading, spacing: 16) {
                            Text(firstName.uppercased())
                                .font(.system(size: 12, weight: .bold, design: .monospaced))
                                .foregroundStyle(Brand.fieldFocus)
                            // Every page participates in layout; revealing glyphs never reflows words.
                            ZStack(alignment: .topLeading) {
                                ForEach(lines.indices, id: \.self) { index in
                                    Text(lines[index]).hidden().accessibilityHidden(true)
                                }
                            }
                            .overlay(alignment: .topLeading) {
                                Text(revealedLine).accessibilityHidden(true)
                            }
                            .font(.system(size: 19, weight: .medium, design: .monospaced))
                            .foregroundStyle(Brand.welcomeTitle)
                            .lineSpacing(6)
                            .fixedSize(horizontal: false, vertical: true)
                            .frame(maxWidth: .infinity, minHeight: 96, alignment: .topLeading)
                            .accessibilityElement(children: .ignore).accessibilityLabel(line)
                            // Reserve the final choices row from the start so the panel never jumps.
                            ZStack(alignment: .trailing) {
                                ViewThatFits(in: .horizontal) {
                                    HStack(spacing: 10) { choices }
                                    VStack(alignment: .leading, spacing: 10) { choices }
                                }
                                .opacity(showingChoices ? 1 : 0)
                                .allowsHitTesting(showingChoices)
                                .disabled(!showingChoices)
                                .accessibilityHidden(!showingChoices)
                                Button("Continue →", action: advance)
                                    .buttonStyle(DialogueActionStyle(primary: true))
                                    .keyboardShortcut(.defaultAction)
                                    .help(complete ? "Next line" : "Reveal the full line")
                                    .opacity(showingChoices ? 0 : 1)
                                    .disabled(showingChoices)
                                    .accessibilityHidden(showingChoices)
                            }.frame(maxWidth: .infinity, alignment: .trailing)
                        }
                    }.padding(12)
                }
                .frame(maxWidth: 960)
                .opacity(presented ? 1 : 0)
                .offset(y: presented || reduceMotion ? 0 : 12)
                .padding(.horizontal, 24)
                .padding(.bottom, 24 + viewport.safeAreaInsets.bottom)
            }.frame(width: viewport.size.width, height: viewport.size.height)
        }
        .onExitCommand(perform: dismiss)
        .onAppear {
            if reduceMotion { presented = true }
            else { withAnimation(.easeOut(duration: Self.entranceDuration)) { presented = true } }
        }
        .task(id: page) {
            let currentPage = page
            let characterCount = lines[currentPage].count
            if reduceMotion { visibleCharacters = characterCount; return }
            // Use elapsed time rather than accumulated sleeps so busy frames don't slow the text.
            let clock = ContinuousClock()
            let start = clock.now
            while visibleCharacters < characterCount {
                do { try await Task.sleep(for: Self.characterDelay) }
                catch { return }
                guard !Task.isCancelled, page == currentPage else { return }
                let elapsed = start.duration(to: clock.now).components
                let seconds = Double(elapsed.seconds) + Double(elapsed.attoseconds) / 1e18
                visibleCharacters = min(characterCount, max(visibleCharacters, Int(seconds / 0.024)))
            }
        }
        .onChange(of: reduceMotion) { _, enabled in if enabled { visibleCharacters = line.count } }
    }
    @ViewBuilder private var choices: some View {
        Button("Find my people") { choose(.people) }.buttonStyle(DialogueActionStyle(primary: false))
        Button("Explore side quests") { choose(.sideEvents) }.buttonStyle(DialogueActionStyle(primary: false))
        Button("Plan my day") { choose(.plan) }.buttonStyle(DialogueActionStyle(primary: true))
    }
    private func advance() {
        if !complete { visibleCharacters = line.count }
        else if !lastPage {
            visibleCharacters = reduceMotion ? lines[page + 1].count : 0
            page += 1
        }
    }
}
