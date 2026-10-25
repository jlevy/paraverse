import SwiftUI
import AppKit

// An illustrated interpretation of Universe's published experiences, not a venue floor plan.
enum UniverseSpace: Int, CaseIterable, Identifiable {
    case stage, expo, lounge, makers, openSource, recess
    var id: Int { rawValue }
    var title: String { ["Main stage", "Sales floor", "Discussions lounge", "Experiment & play", "Open source", "Recess & coffee"][rawValue] }
    var subtitle: String { ["Ideas worth gathering for", "GitHub Central · demos & discovery", "Expert Center · meet your people", "Makerspace · hack your badge", "Projects, people, possibilities", "A little room for serendipity"][rawValue] }
    var detail: String { [
        "Start with the big ideas, then build a day around what interests you. Open your schedule to explore sessions with the Universe assistant.",
        "Explore the product side of Universe: Copilot, Actions, security, and the people behind the tools. GitHub Central brings demos and expert conversations together. This sales floor is our interpretation of that experience.",
        "Pull up a chair. Inspired by the Expert Center and Universe’s community spaces, this lounge is for technical questions and finding people with shared interests.",
        "Make something just for the fun of it. Universe’s Makerspace brings code into art, music, and robotics, while Hack your badge turns your conference pass into a project of its own.",
        "Meet the community behind the code. The Open Source Zone celebrates maintainers, contributors, and projects you might want to help build.",
        "Take a breather between sessions. Universe’s Recess makes space for shared interests, casual conversations, and playful activities. Here, the café is your meeting point."
    ][rawValue] }
    var rect: CGRect { [CGRect(x: 42,y: 80,width: 295,height: 190), CGRect(x: 667,y: 80,width: 287,height: 190), CGRect(x: 42,y: 310,width: 295,height: 160), CGRect(x: 667,y: 310,width: 287,height: 160), CGRect(x: 382,y: 80,width: 240,height: 190), CGRect(x: 382,y: 310,width: 240,height: 160)][rawValue] }
    var entrance: CGPoint { CGPoint(x: rect.midX, y: 290) }
    var tint: Color { worldColor([0xB9AFE2,0x85C9C0,0xE6B295,0xD2C475,0xA3C185,0xDBA3A9][rawValue]) }
}

private func worldColor(_ hex: UInt32) -> Color { Color(red: Double((hex >> 16) & 255)/255, green: Double((hex >> 8) & 255)/255, blue: Double(hex & 255)/255) }

struct LegacyUniverseWorld: View {
    var openSchedule: () -> Void
    var openPeople: () -> Void
    var openAssistant: () -> Void
    var openDiscovery: () -> Void
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    private static let artwork: NSImage? = {
        if let url = Bundle.main.url(forResource: "UniverseInterior", withExtension: "png") { return NSImage(contentsOf: url) }
        let url = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("Assets/UniverseInterior.png")
        return NSImage(contentsOf: url)
    }()
    @State private var hovered: UniverseSpace?
    @State private var selected: UniverseSpace?
    @State private var player = CGPoint(x: 500, y: 290)
    @State private var paused = false
    @FocusState private var mapFocused: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("A little universe. A lot to discover.").font(.system(size: 27, weight: .medium, design: .serif))
                    Text("GitHub Universe  ·  Fort Mason, San Francisco").font(.subheadline).foregroundStyle(.secondary)
                }
                Spacer()
                Button("All conferences", action: openDiscovery).buttonStyle(.bordered)
            }.padding(24)
            HStack {
                Label("Explore the hall", systemImage: "map").font(.subheadline.weight(.medium))
                Spacer()
                Menu("Go to a space") {
                    ForEach(UniverseSpace.allCases) { zone in Button(zone.title) { visit(zone) } }
                }.fixedSize()
                Button { paused.toggle() } label: { Image(systemName: paused ? "play.fill" : "pause.fill") }
                    .help(paused ? "Resume ambient activity" : "Pause ambient activity")
                    .accessibilityLabel(paused ? "Resume ambient activity" : "Pause ambient activity")
            }.padding(.horizontal, 24).padding(.bottom, 12)
            GeometryReader { geometry in
                let scale = min(geometry.size.width / 1000, geometry.size.height / 680)
                ZStack {
                    if let artwork = Self.artwork {
                        Image(nsImage: artwork).resizable().interpolation(.none).frame(width: 1000, height: 680).accessibilityHidden(true)
                    }
                    TimelineView(.animation(minimumInterval: 1.0/15, paused: paused || reduceMotion)) { timeline in
                        Canvas { context, _ in
                            var painter = UniversePainter(context: context)
                            if Self.artwork == nil {
                                painter.draw(time: 0, player: player)
                            } else {
                                painter.visitors(time: paused || reduceMotion ? 0 : timeline.date.timeIntervalSinceReferenceDate, player: player)
                            }
                        }
                    }.accessibilityHidden(true)
                    ForEach(UniverseSpace.allCases) { zone in
                        Button { visit(zone) } label: {
                            Rectangle().fill(.white.opacity(hovered == zone ? 0.09 : 0.001))
                                .overlay(alignment: .bottom) {
                                    Text(zone.title + " ↗")
                                        .font(.system(size: 13, weight: .semibold, design: .monospaced))
                                        .padding(9).background(worldColor(0x272D30), in: RoundedRectangle(cornerRadius: 4))
                                        .opacity(hovered == zone || selected == zone ? 1 : 0)
                                }
                        }.buttonStyle(.plain)
                            .frame(width: zone.rect.width, height: zone.rect.height)
                            .position(x: zone.rect.midX, y: zone.rect.midY)
                            .onHover { inside in hovered = inside ? zone : nil }
                            .accessibilityLabel(zone.title).help(zone.subtitle)
                    }
                    Text("YOU").font(.system(size: 9, weight: .bold, design: .monospaced))
                        .padding(4).background(worldColor(0x272D30)).position(x: player.x, y: player.y - 33).allowsHitTesting(false)
                }
                .frame(width: 1000, height: 680)
                .contentShape(Rectangle())
                .onTapGesture { location in
                    mapFocused = true
                    if let zone = UniverseSpace.allCases.first(where: { $0.rect.contains(location) }) { visit(zone) }
                    else { move(to: location) }
                }
                .focusable().focused($mapFocused).focusEffectDisabled()
                .onKeyPress(.leftArrow) { move(to: CGPoint(x: player.x - 12, y: player.y)); return .handled }
                .onKeyPress(.rightArrow) { move(to: CGPoint(x: player.x + 12, y: player.y)); return .handled }
                .onKeyPress(.upArrow) { move(to: CGPoint(x: player.x, y: player.y - 12)); return .handled }
                .onKeyPress(.downArrow) { move(to: CGPoint(x: player.x, y: player.y + 12)); return .handled }
                .onKeyPress(.escape) { selected = nil; return .handled }
                .scaleEffect(scale)
                .frame(width: geometry.size.width, height: geometry.size.height, alignment: .center)
                .clipped()
            }.background(worldColor(0x26383D))
            if let zone = selected { detail(zone) }
            HStack {
                Text("Click a space to explore · Click a path or use arrow keys to move")
                Spacer()
                Text("Illustrated world · Simulated visitors")
            }.font(.caption).foregroundStyle(.secondary).padding(.horizontal, 24).padding(.vertical, 13)
        }.background(Brand.canvas)
    }

    private func visit(_ zone: UniverseSpace) { selected = zone; player = zone.entrance }
    private func move(to point: CGPoint) {
        let next = CGPoint(x: min(963, max(32, point.x)), y: min(650, max(286, point.y)))
        let aisles = [CGRect(x: 30, y: 286, width: 936, height: 17),
                      CGRect(x: 345, y: 278, width: 30, height: 201),
                      CGRect(x: 630, y: 278, width: 28, height: 201),
                      CGRect(x: 345, y: 471, width: 313, height: 9),
                      CGRect(x: 465, y: 471, width: 70, height: 180),
                      CGRect(x: 30, y: 615, width: 936, height: 36)]
        guard aisles.contains(where: { $0.contains(next) }) else { return }
        player = next
    }
    private func detail(_ zone: UniverseSpace) -> some View {
        HStack(alignment: .top, spacing: 18) {
            Text(String(format: "%02d", zone.rawValue + 1)).font(.system(size: 30, design: .monospaced)).foregroundStyle(zone.tint)
            VStack(alignment: .leading, spacing: 7) {
                Text(zone.title).font(.headline)
                Text(zone.detail).font(.subheadline).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                HStack {
                    if zone == .stage { Button("Explore my schedule", action: openSchedule) }
                    else if zone == .lounge || zone == .openSource || zone == .recess { Button("Find people to meet", action: openPeople) }
                    else { Button("Explore with assistant", action: openAssistant) }
                    Link("About the Universe spaces", destination: URL(string: "https://github.blog/news-insights/company-news/explore-the-best-of-github-universe-9-spaces-built-to-spark-creativity-connection-and-joy/")!)
                }.buttonStyle(.bordered).padding(.top, 3)
            }
            Spacer(minLength: 0)
            Button { selected = nil } label: { Image(systemName: "xmark") }.buttonStyle(.plain).accessibilityLabel("Close space details")
        }.padding(20).background(.white.opacity(0.035))
    }
}

// Small rectilinear sprites keep the world crisp without borrowing Simile's artwork.
private struct UniversePainter {
    var context: GraphicsContext
    mutating func box(_ x: Double, _ y: Double, _ w: Double, _ h: Double, _ color: UInt32) {
        context.fill(Path(CGRect(x: x.rounded(), y: y.rounded(), width: w, height: h)), with: .color(worldColor(color)))
    }
    mutating func label(_ text: String, _ x: Double, _ y: Double, _ size: Double = 12, _ color: UInt32 = 0x344345) {
        context.draw(Text(text).font(.system(size: size, weight: .bold, design: .monospaced)).foregroundColor(worldColor(color)), at: CGPoint(x: x, y: y))
    }
    mutating func tree(_ x: Double, _ y: Double) {
        box(x-13,y+16,30,8,0xA9AE91); box(x-3,y,7,23,0x795E45)
        box(x-17,y-20,34,31,0x496E53); box(x-22,y-13,44,17,0x496E53)
        box(x-14,y-24,26,25,0x779660); box(x-18,y-15,27,13,0x8BA76E)
        box(x-8,y-20,8,7,0xA2B67D); box(x+10,y-5,7,10,0x365E4B)
    }
    mutating func person(_ x: Double, _ y: Double, _ shirt: UInt32, _ phase: Double = 0) {
        box(x-7,y+9,17,4,0x9D9C88)
        box(x-5,y+3,4,9 + phase,0x34414D); box(x+2,y+3,4,9-phase,0x34414D)
        box(x-7,y-9,15,15,shirt); box(x-10,y-7,3,10,0xDAA780); box(x+8,y-7,3,10,0xDAA780)
        box(x-6,y-21,13,13,0xE5B78E); box(x-7,y-24,14,6,0x493D3B); box(x-7,y-20,3,7,0x493D3B)
        box(x+3,y-17,2,2,0x343539); box(x-1,y-7,2,7,0xEEE6D5); box(x-2,y-1,5,4,0xE7DBB7)
    }
    mutating func bench(_ x: Double, _ y: Double) {
        box(x+4,y+10,4,16,0x525B53); box(x+48,y+10,4,16,0x525B53)
        box(x,y,56,7,0xA77550); box(x,y+9,56,6,0xC49366); box(x-2,y+17,60,6,0xB88458)
    }
    mutating func room(_ r: CGRect, _ wall: UInt32, _ floor: UInt32) {
        let x = r.minX, y = r.minY, w = r.width, h = r.height
        box(x+9,y+12,w,h,0xABA995); box(x,y,w,h,0x545C58); box(x+4,y+4,w-8,h-8,floor)
        for line in stride(from: y+17, to: y+h-4, by: 15) { box(x+4,line,w-8,1,0xBFB9A3) }
        box(x,y,w,13,wall); box(x,y,7,h,wall); box(x+w-7,y,7,h,wall)
        box(x,y+h-8,w/2-23,8,wall); box(x+w/2+23,y+h-8,w/2-23,8,wall)
    }
    mutating func desk(_ x: Double, _ y: Double, _ color: UInt32) {
        box(x+3,y+8,69,31,0x9A978A); box(x,y,68,28,color); box(x,y+27,68,8,0x876F5A)
        box(x+21,y-8,26,19,0x38474B); box(x+24,y-5,20,12,0x82BABC); box(x+30,y+12,14,3,0xE8DED1)
    }
    mutating func visitors(time: Double, player: CGPoint) {
        for i in 0..<17 {
            let progress = (time * (5 + Double(i % 3)) + Double(i) * 53).truncatingRemainder(dividingBy: 880)
            let x = 60 + (i % 2 == 0 ? progress : 880 - progress)
            let y = i % 3 == 0 ? 635.0 : (i % 3 == 1 ? 290.0 : 299.0)
            detailedPerson(x, y, [0x92729D,0x446C87,0xAB6351,0x6B8253,0xBD984D][i % 5], sin(time * 5 + Double(i)))
        }
        detailedPerson(player.x, player.y, 0xC98A43, 0)
    }
    mutating func detailedPerson(_ x: Double, _ y: Double, _ shirt: UInt32, _ step: Double) {
        box(x-6,y+7,13,3,0x9F9688)
        box(x-5,y,4,9,0x343D46); box(x+1,y,4,9,0x343D46)
        box(x-6,y+7+step,5,2,0x302D32); box(x+1,y+7-step,5,2,0x302D32)
        box(x-6,y-10,12,13,0x38363B); box(x-5,y-9,10,10,shirt)
        box(x-7,y-7,2,8,0xBD906D); box(x+6,y-7,2,8,0xBD906D)
        box(x-5,y-21,10,12,0x473A35); box(x-6,y-19,12,7,0x473A35)
        box(x-4,y-18,8,8,0xD4A27B); box(x-3,y-17,6,5,0xE6BA91)
        box(x-5,y-21,9,4,0x4B3C35); box(x-3,y-22,6,2,0x655044)
        box(x-4,y-18,2,3,0x4B3C35); box(x+2,y-15,1,2,0x343239)
        box(x-1,y-8,1,6,0xE2D9CC); box(x-2,y-3,3,4,0xEDE4D1)
    }
    mutating func draw(time: Double, player: CGPoint) {
        box(0,0,1000,680,0x6D9FAD)
        for i in 0..<75 {
            let x = Double((i * 137) % 1000), y = Double(630 + (i * 17) % 49)
            box(x + sin(time * 0.3 + Double(i))*4,y,Double(8+i%17),2,0x94BAC0)
        }
        box(18,20,964,605,0x646E64); box(24,26,952,593,0xDDD4BC)
        for y in stride(from: 30.0, to: 620, by: 18) {
            box(25,y,950,1,0xC9C3AD)
            for x in stride(from: 30.0, to: 975, by: 36) { box(x + (Int(y)%36 == 12 ? 18 : 0),y,1,18,0xC9C3AD) }
        }
        box(38,316,924,45,0xEAE0C8); box(347,40,24,545,0xEAE0C8); box(630,40,23,545,0xEAE0C8)
        for x in stride(from: 42.0, to: 970, by: 26) { box(x,609,12,6,0x737D72) }
        label("F O R T   M A S O N   •   S A N   F R A N C I S C O",500,651,12,0xE2E9D9)
        room(UniverseSpace.stage.rect,0x877EAA,0xD2CBDB)
        box(83,89,262,76,0x3E4055); box(91,94,246,56,0x222F39)
        label("GITHUB",214,112,13,0xD4DDC8); label("UNIVERSE",214,137,26,0xD3C4EA)
        box(90,164,248,9,0xA899BA)
        for row in 0..<4 { for col in 0..<9 { box(93+Double(col)*28,186+Double(row)*20,17,12,0x877F9B); box(93+Double(col)*28,197+Double(row)*20,17,3,0x625F77) } }
        room(UniverseSpace.expo.rect,0x609E9A,0xD2DDD2)
        for row in 0..<2 { for col in 0..<3 { desk(654+Double(col)*91,116+Double(row)*89,[0x8FBAB4,0xACA3C5,0xC5B779][col]) } }
        label("COPILOT     ACTIONS     SECURITY",785,91,10)
        room(UniverseSpace.openSource.rect,0x7F9E69,0xDBDEC0)
        label("< / >",500,100,25,0x587253)
        desk(399,133,0xACBF8D); desk(526,133,0xACBF8D)
        bench(398,202); bench(542,202)
        room(UniverseSpace.lounge.rect,0xB5866C,0xE9D4BC)
        for x in [91.0,233.0] { for y in [406.0,482.0] {
            box(x,y,68,20,0xB88370); box(x+4,y-5,60,10,0xD1A18C)
            box(x+9,y+34,48,21,0xAF956D); box(x+16,y+36,6,6,0xF2E7C8)
        } }
        room(UniverseSpace.makers.rect,0xB5A057,0xE2DCAD)
        desk(686,411,0xC5B770); desk(838,411,0xC5B770)
        desk(686,491,0xC5B770); desk(838,491,0xC5B770)
        box(787,461,27,27,0x697E82); box(791,447,19,17,0x8FAEB1); box(795,451,4,4,0xF2D188); box(804,451,4,4,0xF2D188)
        label("MAKE SOMETHING",801,390,10)
        box(383,439,234,130,0xB5C595)
        for x in [402.0,540.0] { bench(x,465); bench(x,525) }
        box(468,467,65,42,0xB57F61); box(463,458,75,13,0xEEE0BA)
        for i in 0..<5 { box(463+Double(i)*15,458,8,13,0xCE8E75) }
        label("COFFEE",500,490,10,0xFFF1D2)
        for (x,y) in [(48.0,82.0),(47,269),(951,85),(952,276),(46,418),(47,557),(950,416),(950,558),(393,593),(609,593),(391,278),(610,278)] { tree(x,y) }
        label("← DISCOVER",132,338,11,0x8D8776); label("CONNECT →",855,338,11,0x8D8776)
        label("PARAVERSE",500,324,21,0x626F61); label("MEET HERE. GO ANYWHERE.",500,345,9,0x868A75)
        for i in 0..<23 {
            let progress = (time * (7 + Double(i%3)) + Double(i)*41).truncatingRemainder(dividingBy: 870)
            let x = 65 + (i%2 == 0 ? progress : 870-progress)
            let y = i%3 == 0 ? 588.0 : (i%3 == 1 ? 302.0 : 385.0)
            person(x,y,[0x9B7DAA,0x557D89,0xAD795F,0x72895A,0xC5A65B][i%5],sin(time*5+Double(i))*1.5)
        }
        for (x,y,c) in [(180.0,444.0,UInt32(0x718A69)),(267,463,0xA47AA0),(765,144,0x7786A0),(555,188,0xAD795F),(855,471,0x6F968F),(423,512,0xA98265)] { person(x,y,c) }
        person(player.x,player.y,0xDB9B57)
    }
}
