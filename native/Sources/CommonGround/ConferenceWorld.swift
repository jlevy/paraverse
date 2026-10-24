import SwiftUI
import SpriteKit
import AppKit

func worldAsset(_ path: String) -> URL {
    let bundled = Bundle.main.resourceURL!.appendingPathComponent(path)
    if FileManager.default.fileExists(atPath: bundled.path) { return bundled }
    return URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("Assets/" + path)
}
struct WorldSpeaker: Codable, Identifiable {
    struct Session: Codable, Identifiable { let id, title, date, start, room, url: String }
    let id, name, role, company, biography, sourceURL: String
    let photo: String?
    var linkedinURL: String?
    var xURL: String?
    var githubURL: String?
    let sessions: [Session]
    var attendee: Bool?
    var avatarAsset: String?
    var avatarNote: String?
    var isJudge: Bool { id.hasPrefix("ptc-judge:") }
    var directorySummary: String {
        if isJudge { return [company, "Patch the Conference"].filter { !$0.isEmpty }.joined(separator: " · ") }
        return [attendee == true ? "Attendee" : "Speaker", company, role]
            .filter { !$0.isEmpty }
            .reduce(into: [String]()) { result, item in
                if !result.contains(where: { $0.caseInsensitiveCompare(item) == .orderedSame }) { result.append(item) }
            }.joined(separator: " · ")
    }
    func matchesDirectorySearch(_ query: String) -> Bool {
        let term = query.trimmingCharacters(in: .whitespacesAndNewlines)
        let category = isJudge ? "judge judges" : (attendee == true ? "attendee attendees" : "speaker speakers")
        return term.isEmpty || "\(name) \(company) \(role) \(biography) \(category)".localizedCaseInsensitiveContains(term)
    }
    static func directoryOrder(_ lhs: WorldSpeaker, _ rhs: WorldSpeaker) -> Bool {
        let leftPlaceholder = lhs.isJudge && lhs.avatarNote != nil
        let rightPlaceholder = rhs.isJudge && rhs.avatarNote != nil
        if leftPlaceholder != rightPlaceholder { return !leftPlaceholder }
        return lhs.name.localizedCaseInsensitiveCompare(rhs.name) == .orderedAscending
    }
    static let all: [WorldSpeaker] = (try? JSONDecoder().decode([WorldSpeaker].self, from: Data(contentsOf: worldAsset("world-speakers.json")))) ?? []
    static let judges: [WorldSpeaker] = (try? JSONDecoder().decode([WorldSpeaker].self, from: Data(contentsOf: worldAsset("ptc-judges.json")))) ?? []
    static let directoryPeople: [WorldSpeaker] = {
        let known = (try? PublicAttendee.load()) ?? []
        let speakers = all
        let extras = known.filter { person in
            !speakers.contains { speaker in
                (speaker.xURL != nil && speaker.xURL?.lowercased() == person.profile_url.lowercased()) ||
                (speaker.linkedinURL != nil && speaker.linkedinURL?.lowercased() == person.linkedin_url?.lowercased())
            }
        }.map { person in
            WorldSpeaker(id:"attendee:" + person.id,name:person.name,role:person.role ?? "Attendee",company:"",biography:person.about ?? person.evidence,sourceURL:person.source_url,photo:nil,linkedinURL:person.linkedin_url,xURL:person.profile_url,githubURL:person.github_url,sessions:[],attendee:true,avatarAsset:person.avatar_asset)
        }
        return (speakers + extras + judges).sorted(by: directoryOrder)
    }()

}
struct WorldCharacter: Codable {
    let personID: String
    let roles: [String]
    let sprite: String
    var atlasCell: Int?
    static let all: [WorldCharacter] = (try? JSONDecoder().decode([WorldCharacter].self, from: Data(contentsOf: worldAsset("WorldArt/characters.json")))) ?? []
}

struct UniverseWorld: View {
    let profile: AttendeeProfile
    @State private var welcomeVisible = false
    @State private var welcomeReplayID = UUID()
    @Bindable var planner: Planner
    @Binding var assistantOpen: Bool
    var saveCalendar: ([PlannedSession]) -> Void
    @State private var planTab = false
    var openSchedule: () -> Void
    var openPeople: () -> Void
    var openAssistant: () -> Void
    var openDiscovery: () -> Void
    @State private var scene = ConferenceScene()
    @State private var selected: WorldSpeaker?
    @State private var directory = false
    @State private var search = ""
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var ambientPaused = false
    var body: some View {
        GeometryReader { viewport in
        ZStack(alignment:.top) {
            ConferenceSurface(scene:scene)
                .onAppear { scene.selectSpeaker = { selected = $0 }; scene.ambientPaused = ambientPaused || reduceMotion }
                .frame(maxWidth:.infinity,maxHeight:.infinity)
            VStack(spacing:12) {
                HStack(alignment:.top,spacing:12) {
                        WorldPlaque {
                            VStack(alignment:.leading,spacing:4) {
                                Text("GITHUB UNIVERSE").font(.system(size:20,weight:.heavy,design:.monospaced)).foregroundStyle(Color(red:0.96,green:0.87,blue:0.68))
                            }
                        }
                        Spacer(minLength:8)
                        ViewThatFits(in:.horizontal) {
                            HStack(spacing:10) { primaryControls }
                            VStack(alignment:.trailing,spacing:10) { primaryControls }
                        }
                }
                Spacer(minLength:0)
                    HStack(alignment:.bottom) {
                        Spacer(minLength:8)
                        ViewThatFits(in:.horizontal) {
                            HStack(spacing:8) { cameraControls }
                            VStack(alignment:.trailing,spacing:8) { cameraControls }
                        }
                    }
            }.padding(20)
                // The SpriteKit host extends under the unified macOS toolbar, whose inset can report zero.
                .padding(.top, max(52, viewport.safeAreaInsets.top))
                .padding(.bottom, viewport.safeAreaInsets.bottom)
        }.frame(width: viewport.size.width, height: viewport.size.height)
        .clipped()
        .background(Brand.canvas)
        .allowsHitTesting(!assistantOpen)
        .accessibilityHidden(assistantOpen)
        .onAppear {
            welcomeReplayID = UUID()
            welcomeVisible = true
            assistantOpen = false
        }
        .onChange(of: reduceMotion) { _, value in scene.ambientPaused = ambientPaused || value }
        .onChange(of: assistantOpen, initial: true) { _, open in
            scene.inputSuspended = open
            if open { scene.keys.removeAll(); scene.path = [] }
        }
        .overlay {
            if welcomeVisible {
                ParallelWelcome(profile: profile, choose: { destination in
                    dismissWelcome()
                    switch destination {
                    case .plan:
                        planTab = false; assistantOpen = true
                        if !planner.busy { planner.generate(completePlan: true) }
                    case .people: directory = true
                    case .sideEvents:
                        planTab = false; assistantOpen = true
                        if !planner.busy { planner.generate(request: "Find side events that fit my interests and conference schedule.", external: true) }
                    }
                }, dismiss: dismissWelcome).id(welcomeReplayID)
            }
        }
        .overlay {
            if assistantOpen {
                GeometryReader { geo in
                    ZStack {
                        Color.black.opacity(0.45)
                            .contentShape(Rectangle())
                            .onTapGesture { assistantOpen = false }
                            .accessibilityHidden(true)
                        WorldPlannerPanel(planner:planner,showPlan:$planTab,close:{assistantOpen=false},saveCalendar:saveCalendar,openSpeaker:{ selected = $0 })
                            .frame(width:min(690,geo.size.width-48),height:min(680,geo.size.height-48))
                    }.frame(maxWidth:.infinity,maxHeight:.infinity)
                }
                .opacity(selected == nil ? 1 : 0)
                .allowsHitTesting(selected == nil)
                .accessibilityHidden(selected != nil)
            }
        }
        .overlay {
            if let person=selected {
                GeometryReader { geo in
                    ZStack {
                        Color.black.opacity(0.45).onTapGesture {selected=nil}
                        WorldPlaque { speakerProfile(person) }
                            .frame(width:min(690,geo.size.width-48),height:min(680,geo.size.height-48))
                    }.frame(maxWidth:.infinity,maxHeight:.infinity)
                }.onExitCommand {selected=nil}
            }
        }
        .overlay {
            if directory {
                GeometryReader { geo in
                    ZStack {
                        Color.black.opacity(0.35).onTapGesture {directory=false}
                        WorldPlaque { speakerDirectory }
                            .frame(width:min(690,geo.size.width-32),height:min(650,geo.size.height-32))
                    }.frame(maxWidth:.infinity,maxHeight:.infinity)
                }.onExitCommand {directory=false}
            }
        }

    }
    }
    private func dismissWelcome() {
        welcomeVisible = false
    }
    private var speakerDirectory:some View {
            VStack(alignment: .leading, spacing: 16) {
                HStack { Text("ATTENDEES").font(.system(size:20,weight:.bold,design:.monospaced)); Spacer(); Button("CLOSE") { directory = false }.buttonStyle(WorldButtonStyle()) }
                HStack(spacing: 10) {
                    PixelSearchIcon().fill(Brand.welcomeSubtitle).frame(width: 16, height: 16).accessibilityHidden(true)
                    TextField("Search speakers, attendees, and judges", text: $search).textFieldStyle(.plain)
                }
                .padding(12)
                .background(PixelPanel().fill(.black.opacity(0.18)))
                .overlay(PixelPanel().stroke(Brand.fieldBorder, lineWidth: 1))
                ScrollView {
                    LazyVStack(spacing: 2) {
                        ForEach(WorldSpeaker.directoryPeople.filter { $0.matchesDirectorySearch(search) }) { person in
                            Button { directory = false; selected = person } label: {
                                HStack(spacing: 12) {
                                    portrait(person).frame(width: 44, height: 52).accessibilityHidden(true)
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(person.name).font(.system(size: 14, weight: .semibold))
                                        Text(person.directorySummary).font(.system(size: 12)).foregroundStyle(Brand.welcomeSubtitle).lineLimit(2)
                                    }
                                    Spacer(minLength: 8)
                                    Image(systemName: "chevron.right").font(.system(size: 11, weight: .semibold)).foregroundStyle(Brand.welcomeSubtitle)
                                }.padding(.horizontal, 12).padding(.vertical, 8).frame(maxWidth: .infinity, alignment: .leading)
                            }.buttonStyle(DirectoryRowStyle())
                        }
                    }
                }

            }.padding(12).foregroundStyle(Color(red:0.96,green:0.91,blue:0.80))
    }
    @ViewBuilder private var primaryControls:some View {
        Button {
            dismissWelcome()
            directory = false
            selected = nil
            planTab = false
            assistantOpen = true
            planner.generate(completePlan: true)
        } label: { Label("PLAN MY DAY", systemImage: "sparkles") }
            .buttonStyle(WorldButtonStyle(teal: true))
            .help("Generate sessions, people to meet, and external events")
        Button {
            assistantOpen = false
            directory = false
            selected = nil
            welcomeReplayID = UUID()
            welcomeVisible = true
        } label: { Label("REPLAY INTRO", systemImage: "arrow.counterclockwise") }
            .buttonStyle(WorldButtonStyle()).help("Restart the dialogue from the beginning")
            .accessibilityLabel("Replay intro")
        Button { planTab=false;assistantOpen=true } label: { Text("CHAT") }.buttonStyle(WorldButtonStyle(teal:true)).help("Chat and plan your day").keyboardShortcut("j",modifiers:.command)
        Button { directory=true } label: { Label("ATTENDEES",systemImage:"person.2.fill") }.buttonStyle(WorldButtonStyle())
    }
    @ViewBuilder private var cameraControls:some View {
        Button { scene.zoom(by: 0.8) } label: { Image(systemName: "plus.magnifyingglass") }
            .buttonStyle(WorldButtonStyle()).accessibilityLabel("Zoom in").help("Zoom in")
        Button { scene.zoom(by: 1.25) } label: { Image(systemName: "minus.magnifyingglass") }
            .buttonStyle(WorldButtonStyle()).accessibilityLabel("Zoom out").help("Zoom out to the venue edges")
        Button { ambientPaused.toggle();scene.ambientPaused=ambientPaused || reduceMotion } label: {
            Image(systemName:ambientPaused ? "play.fill":"pause.fill")
        }.buttonStyle(WorldButtonStyle())
            .accessibilityLabel(ambientPaused ? "Resume activity":"Pause activity")
    }
    @ViewBuilder private func portrait(_ person: WorldSpeaker) -> some View {
        if let image = WorldCharacter.image(for: person.id) {
            Image(nsImage: image).resizable().interpolation(.none).scaledToFit()
        }
    }
    private func speakerProfile(_ person: WorldSpeaker) -> some View {
        VStack(alignment:.leading,spacing:20) {
            HStack(alignment:.top,spacing:18) {
                portrait(person).frame(width:90,height:90).clipShape(PixelPanel()).overlay(PixelPanel().stroke(Color(red:0.74,green:0.58,blue:0.38),lineWidth:2))
                VStack(alignment:.leading,spacing:6) { Text((WorldCharacter.all.first { $0.personID == person.id }?.roles ?? [person.attendee == true ? "attendee" : "speaker"]).joined(separator: " · ").uppercased()).font(.caption).foregroundStyle(.secondary); Text(person.name).font(.system(size:23,weight:.bold,design:.monospaced)); Text(person.role); Text(person.company).foregroundStyle(.secondary) }
                Spacer(); Button { selected = nil } label: { Image(systemName: "xmark") }.buttonStyle(PlannerQuietButtonStyle()).accessibilityLabel(assistantOpen ? "Back to recommendations" : "Close profile")
            }
            if !person.isJudge {
            Button(person.attendee == true ? "ASK ABOUT THIS PERSON" : "PLAN AROUND THIS SPEAKER") {
                planner.prompt = person.attendee == true ? "What do I have in common with " + person.name + "?" : "Help me plan my day around sessions by " + person.name + "."
                selected=nil;planTab=false;assistantOpen=true
            }.buttonStyle(WorldButtonStyle(teal:true))
            }
            ScrollView { VStack(alignment:.leading,spacing:18) {
                if let note = person.avatarNote { Text(note).font(.caption).foregroundStyle(.secondary) }
                WorldSocialLinks(linkedin:person.linkedinURL,x:person.xURL,github:person.githubURL)
                if !person.biography.isEmpty { Text(person.biography).textSelection(.enabled) }
                if !person.sessions.isEmpty { Text("SESSIONS AT UNIVERSE").font(.system(size:13,weight:.bold,design:.monospaced)) }
                ForEach(person.sessions) { session in
                    VStack(alignment:.leading,spacing:5) {
                        if let url = URL(string:session.url) { Link(session.title,destination:url).font(.headline) } else { Text(session.title) }
                        Text([session.date,session.start,session.room].filter{ !$0.isEmpty }.joined(separator:" · ")).font(.caption).foregroundStyle(.secondary)
                    }
                }
                if let url = URL(string:person.sourceURL) { Link(person.isJudge ? "Official judging panel ↗" : (person.attendee == true ? "Public attendance post ↗" : "Official speaker profile ↗"),destination:url) }
                Text("Character artwork and location are illustrative. This is not live attendance or an exact venue map.").font(.caption).foregroundStyle(.secondary)
            }.frame(maxWidth:.infinity,alignment:.leading) }
        }.padding(10)
        .foregroundStyle(Color(red:0.96,green:0.91,blue:0.80))
    }
}

struct ConferenceSurface: NSViewRepresentable {
    let scene: ConferenceScene
    func makeNSView(context: Context) -> HallView {
        let view = HallView(); view.presentScene(scene); view.preferredFramesPerSecond = 60
        view.setAccessibilityLabel("Walkable conference. Use arrows or WASD, scroll to zoom, or use the Attendees button to browse accessible profiles.")
        return view
    }
    func updateNSView(_ view: HallView, context: Context) {}
    static func dismantleNSView(_ view: HallView, coordinator: ()) { (view.scene as? ConferenceScene)?.keys.removeAll(); view.presentScene(nil) }
}
final class HallView: SKView {
    override var acceptsFirstResponder: Bool { true }
    override func keyDown(with event:NSEvent) {
        guard (scene as? ConferenceScene)?.inputSuspended != true else { super.keyDown(with: event); return }
        guard !event.modifierFlags.contains(.command), [0,1,2,13,123,124,125,126].contains(event.keyCode) else { super.keyDown(with:event); return }
        (scene as? ConferenceScene)?.keys.insert(event.keyCode)
    }
    override func rightMouseDragged(with event:NSEvent) {
        guard let s=scene as? ConferenceScene else{return}
        s.followPlayer=false
        s.cameraNode.position.x -= event.deltaX*s.cameraNode.xScale
        s.cameraNode.position.y += event.deltaY*s.cameraNode.yScale
        s.clampCamera()
    }
    override func keyUp(with event:NSEvent) { (scene as? ConferenceScene)?.keys.remove(event.keyCode) }
    override func resignFirstResponder() -> Bool { (scene as? ConferenceScene)?.keys.removeAll(); return super.resignFirstResponder() }
    override func mouseDown(with event:NSEvent) { window?.makeFirstResponder(self); guard let s = scene as? ConferenceScene else { return }; s.clicked(s.convertPoint(fromView:convert(event.locationInWindow,from:nil))) }
    override func scrollWheel(with event:NSEvent) { (scene as? ConferenceScene)?.zoom(by: exp(event.scrollingDeltaY * 0.008)) }
    override func magnify(with event:NSEvent) { (scene as? ConferenceScene)?.zoom(by:max(0.2,1-event.magnification)) }
}

@MainActor final class ConferenceScene: SKScene {
    let extent = CGSize(width:2200,height:1100)
    var ambientPaused = false
    var inputSuspended = false
    let cameraNode = SKCameraNode()
    let player = SKNode()
    var keys = Set<UInt16>()
    var followPlayer = true
    var selectSpeaker: ((WorldSpeaker)->Void)?
    var obstacles = [CGRect]()
    var path = [CGPoint]()
    private var lastTime:TimeInterval = 0
    private var built = false
    private var facing = 0
    private var playerWalkDistance:CGFloat = 0
    private var frames = [[SKTexture]]()
    private var people = [(SKNode,WorldSpeaker)]()
    // Keep a small ambient cast; the directory retains the complete roster.
    private static let ambientCharacterLimit = 12
    private var crowd = ConferenceCrowd(count: min(ConferenceScene.ambientCharacterLimit, WorldSpeaker.all.count))
    var speakerPositions: [String:CGPoint] { Dictionary(uniqueKeysWithValues:people.map{($0.1.id,$0.0.position)}) }
    override init(size:CGSize) { super.init(size:size); scaleMode = .resizeFill; backgroundColor = NSColor(calibratedRed:0.12,green:0.16,blue:0.18,alpha:1) }
    override convenience init() { self.init(size:CGSize(width:1000,height:650)) }
    required init?(coder:NSCoder) { fatalError("Not used") }
    override func didMove(to view:SKView) { guard !built else{return}; built = true; build(); view.window?.makeFirstResponder(view) }
    func color(_ hex:UInt32) -> NSColor { NSColor(red:CGFloat((hex>>16)&255)/255,green:CGFloat((hex>>8)&255)/255,blue:CGFloat(hex&255)/255,alpha:1) }
    // Trim transparent atlas padding so every pose shares a bottom-center pivot.
    func characterTexture(_ image: NSImage) -> SKTexture {
        guard let data = image.tiffRepresentation, let bitmap = NSBitmapImageRep(data: data) else {
            return SKTexture(image: image)
        }
        var minX = bitmap.pixelsWide, minY = bitmap.pixelsHigh, maxX = -1, maxY = -1
        for y in 0..<bitmap.pixelsHigh {
            for x in 0..<bitmap.pixelsWide where (bitmap.colorAt(x: x, y: y)?.alphaComponent ?? 0) > 0.5 {
                minX = min(minX, x); maxX = max(maxX, x)
                minY = min(minY, y); maxY = max(maxY, y)
            }
        }
        guard maxX >= minX, maxY >= minY,
              let cropped = bitmap.cgImage?.cropping(to: CGRect(x: minX, y: minY, width: maxX-minX+1, height: maxY-minY+1)) else {
            return SKTexture(image: image)
        }
        let texture = SKTexture(cgImage: cropped)
        texture.filteringMode = .nearest
        return texture
    }
    func setPose(_ body: SKSpriteNode, texture: SKTexture) {
        let characterHeight: CGFloat = 44
        body.texture = texture
        body.size = CGSize(width: characterHeight * texture.size().width / texture.size().height, height: characterHeight)
    }
    func build() {
        if let image = NSImage(contentsOf:worldAsset("WorldArt/ConnectedCommons.png")) {
            let texture=SKTexture(image:image);texture.filteringMode = .nearest
            let backdrop=SKSpriteNode(texture:texture);backdrop.anchorPoint = .zero
            backdrop.size=extent;backdrop.zPosition = -100;addChild(backdrop)
            // Furniture must cover people walking behind it, just as nearer people do.
            for doorway in CommonsLayout.doorways {
                let opening=SKNode()
                opening.position=CommonsLayout.point(doorway.minX,doorway.maxY)
                opening.zPosition = -90
                let width=doorway.width*2.2,height=doorway.height*2.2
                let tileWidth:CGFloat=44,tileHeight:CGFloat=22
                for x in stride(from:CGFloat.zero,to:width,by:tileWidth) {
                    for y in stride(from:CGFloat.zero,to:height,by:tileHeight) {
                        let w=min(tileWidth,width-x),h=min(tileHeight,height-y)
                        let tile=SKTexture(rect:CGRect(x:0.35,y:0.325,width:0.01*w/tileWidth,height:0.01*h/tileHeight),in:texture)
                        tile.filteringMode = .nearest
                        let plank=SKSpriteNode(texture:tile,size:CGSize(width:w,height:h))
                        plank.anchorPoint = .zero;plank.position=CGPoint(x:x,y:y);opening.addChild(plank)
                    }
                }
                let northSouth=doorway.width>=doorway.height || doorway.minY == 338
                let jambWidth:CGFloat=2
                for edge in [CGFloat.zero,northSouth ? width-jambWidth : height-jambWidth] {
                    let jamb=SKSpriteNode(color:color(0x596B79),size:CGSize(width:northSouth ? jambWidth : width,height:northSouth ? height : jambWidth))
                    jamb.anchorPoint = .zero;jamb.position=northSouth ? CGPoint(x:edge,y:0) : CGPoint(x:0,y:edge)
                    opening.addChild(jamb)
                }
                addChild(opening)
            }
            for footprint in CommonsLayout.occlusionRects {
                let rect = CGRect(x:footprint.minX/1000, y:1-footprint.maxY/500,
                                  width:footprint.width/1000, height:footprint.height/500)
                let detail = SKTexture(rect:rect, in:texture); detail.filteringMode = .nearest
                let foreground = SKSpriteNode(texture:detail)
                foreground.anchorPoint = .zero
                foreground.position = CommonsLayout.point(footprint.minX,footprint.maxY)
                foreground.size = CGSize(width:footprint.width*2.2,height:footprint.height*2.2)
                foreground.zPosition = 1600-foreground.position.y
                addChild(foreground)
            }
        }
        frames = (0..<4).map { row in (0..<3).compactMap { column in
            guard let image=NSImage(contentsOf:worldAsset("WorldArt/player-\(row)-\(column).png")) else{return nil}
            return characterTexture(image)
        } }
        addChild(player);player.position=CommonsLayout.entrance;makeCharacter(player,isPlayer:true)
        for (i,person) in WorldSpeaker.all.prefix(Self.ambientCharacterLimit).enumerated() {
            let walker=crowd.walkers[i]
            let node=SKNode();node.position=walker.position
            makeCharacter(node,isPlayer:false,index:i);addChild(node)
            let name=SKLabelNode(fontNamed:"Menlo-Bold");name.text=person.name;name.fontSize=10
            name.fontColor=color(0xFFFFFF);name.position=CGPoint(x:0,y:50);name.name="caption"
            let plate=SKShapeNode(rectOf:CGSize(width:CGFloat(person.name.count)*6.3+12,height:17),cornerRadius:4)
            plate.fillColor=color(0x252B36);plate.strokeColor = .clear;plate.position=CGPoint(x:0,y:54);plate.name="plate"
            node.addChild(plate);node.addChild(name)
            let activity=SKLabelNode(fontNamed:"Menlo");activity.text="Exploring Universe";activity.fontSize=8
            activity.fontColor=color(0xFFFFFF);activity.position=CGPoint(x:0,y:69);activity.name="activity";node.addChild(activity)
            people.append((node,person))
        }
        addChild(cameraNode);camera=cameraNode;fillViewport()
    }
    func makeCharacter(_ node:SKNode,isPlayer:Bool,index:Int = 0) {
        let shadow=SKShapeNode(ellipseOf:CGSize(width:22,height:8));shadow.fillColor = .black.withAlphaComponent(0.2);shadow.strokeColor = .clear;node.addChild(shadow)
        let custom = isPlayer ? nil : WorldCharacter.all.first { $0.personID == WorldSpeaker.all[index].id }
        let textureURL=worldAsset(custom.map { "WorldArt/" + $0.sprite } ?? "WorldArt/player.png")
        if let image=NSImage(contentsOf:textureURL) {
            let t=characterTexture(image);let sprite=SKSpriteNode(texture:t);setPose(sprite,texture:t);if custom != nil { sprite.size=CGSize(width:32,height:44) };sprite.anchorPoint=CGPoint(x:0.5,y:0);sprite.name="body"
            if !isPlayer && custom == nil { sprite.color=color([0x6EA6B3,0xB58EC6,0xCFA272,0x7EB79E,0xBD8291][index%5]);sprite.colorBlendFactor=0.28 }
            node.addChild(sprite)
        } else {
            let body=SKShapeNode(rectOf:CGSize(width:23,height:30));body.fillColor=color(isPlayer ? 0x418F95 : 0x8D79A5);body.position.y=24;node.addChild(body)
            let head=SKShapeNode(rectOf:CGSize(width:23,height:22));head.fillColor=color(0xBF9276);head.position.y=48;node.addChild(head)
        }
        if isPlayer { let label=SKLabelNode(fontNamed:"Menlo-Bold");label.text="YOU";label.fontSize=12;label.position.y=49;node.addChild(label) }
    }
    // Largest camera scale that still covers the viewport with venue artwork.
    var maximumZoomScale: CGFloat {
        min(extent.width / max(size.width, 1), extent.height / max(size.height, 1))
    }
    func zoom(by factor:CGFloat) { zoomTo(cameraNode.xScale * factor) }
    func zoomTo(_ value:CGFloat) {
        cameraNode.setScale(min(maximumZoomScale, max(min(0.4, maximumZoomScale), value)))
        clampCamera()
    }
    func overview() { fillViewport() }
    func fillViewport() {
        followPlayer = false
        cameraNode.position = CGPoint(x: extent.width / 2, y: extent.height / 2)
        zoomTo(maximumZoomScale)
    }
    override func didChangeSize(_ oldSize:CGSize) {
        if built { zoomTo(cameraNode.xScale) }
    }
    func focus(_ point:CGPoint) { followPlayer=false;cameraNode.position=point;zoomTo(0.65);clampCamera() }
    func clampCamera() {
        let w=min(extent.width/2,size.width*cameraNode.xScale/2), h=min(extent.height/2,size.height*cameraNode.yScale/2)
        cameraNode.position.x=max(w,min(extent.width-w,cameraNode.position.x))
        cameraNode.position.y=max(h,min(extent.height-h,cameraNode.position.y))
    }
    func walkable(_ p:CGPoint) -> Bool { CommonsLayout.walkable(p) }
    func clicked(_ p:CGPoint) {
        if let (_,person)=people.min(by:{ hypot($0.0.position.x-p.x,$0.0.position.y+20-p.y)<hypot($1.0.position.x-p.x,$1.0.position.y+20-p.y) }),let found=people.first(where:{$0.1.id==person.id}),hypot(found.0.position.x-p.x,found.0.position.y+20-p.y)<30 { keys.removeAll();path=[];selectSpeaker?(person);return }
        path=HallNavigation.route(from:player.position,to:p,walkable:walkable);followPlayer=true
    }
    override func update(_ currentTime:TimeInterval) {
        let dt=min(0.04,lastTime == 0 ? 0 : currentTime-lastTime);lastTime=currentTime
        var dx:CGFloat=0,dy:CGFloat=0
        if keys.contains(0)||keys.contains(123){dx -= 1};if keys.contains(2)||keys.contains(124){dx += 1}
        if keys.contains(13)||keys.contains(126){dy += 1};if keys.contains(1)||keys.contains(125){dy -= 1}
        if dx != 0 || dy != 0 { path=[];followPlayer=true }
        else if let target=path.first { dx=target.x-player.position.x;dy=target.y-player.position.y;if hypot(dx,dy)<8 { path.removeFirst();dx=0;dy=0 } }
        let length=hypot(dx,dy)
        let previousPlayerPosition=player.position
        func canStep(_ p:CGPoint)->Bool {
            crowd.graph.clearSegment(player.position,p) && crowd.walkers.allSatisfy {
                $0.position.distance(to:p)>=ConferenceCrowd.personalSpace
            }
        }
        if length>0 {
            let step=min(CGFloat(dt)*180,length>2 ? length : 180)
            let x=CGPoint(x:player.position.x+dx/length*step,y:player.position.y)
            if canStep(x){player.position=x}
            let y=CGPoint(x:player.position.x,y:player.position.y+dy/length*step)
            if canStep(y){player.position=y}
            if abs(dx)>abs(dy) { facing = dx<0 ? 1 : 2 } else { facing = dy>0 ? 3 : 0 }
        }
        let playerStep=player.position.distance(to:previousPlayerPosition)
        playerWalkDistance += playerStep
        if frames.count == 4, frames[facing].count == 3, let body=player.childNode(withName:"body") as? SKSpriteNode {
            let gait=[1,0,1,2],distancePerPose:CGFloat=6
            let pose=playerStep>0.001 ? gait[Int(playerWalkDistance/distancePerPose)%gait.count] : 1
            setPose(body,texture:frames[facing][pose])
        }
        player.zPosition=1600-player.position.y
        if !ambientPaused { crowd.update(dt:dt,player:player.position) }
        let closestSpeaker=crowd.walkers.indices.min {
            crowd.walkers[$0].position.distance(to:player.position)<crowd.walkers[$1].position.distance(to:player.position)
        }
        for (index,item) in people.enumerated() {
            let node=item.0
            node.position=crowd.walkers[index].position
            node.zPosition=1600-node.position.y
            let distance=hypot(node.position.x-player.position.x,node.position.y-player.position.y)
            let near=cameraNode.xScale < 1.25 && distance<110 && index == closestSpeaker
            node.childNode(withName:"caption")?.isHidden = !near
            node.childNode(withName:"plate")?.isHidden = !near
            if let label=node.childNode(withName:"activity") as? SKLabelNode {
                label.text=crowd.walkers[index].activity
                label.isHidden = !near
            }
            if let body=node.childNode(withName:"body") as? SKSpriteNode {
                let custom=WorldCharacter.all.contains{$0.personID==item.1.id}
                if !custom, frames.count==4, frames[crowd.walkers[index].direction].count==3 {
                    // Repeat the standing pose between steps for a balanced left/right gait.
                    let gait = [1, 0, 1, 2]
                    let distancePerPose: CGFloat = 6
                    let pose = gait[Int(crowd.walkers[index].distanceWalked / distancePerPose) % gait.count]
                    setPose(body,texture:frames[crowd.walkers[index].direction][crowd.walkers[index].speed < 1 ? 1 : pose])
                }
                let stride = Double(crowd.walkers[index].distanceWalked) / 6
                body.position.y=custom && crowd.walkers[index].speed > 1 ? abs(sin(stride))*0.7 : 0
                body.zRotation=0
            }
        }
        if followPlayer { let t=min(1,CGFloat(dt)*7);cameraNode.position.x += (player.position.x-cameraNode.position.x)*t;cameraNode.position.y += (player.position.y+80-cameraNode.position.y)*t;clampCamera() }
    }
}

enum HallNavigation {
    static func route(from start:CGPoint,to end:CGPoint,walkable:(CGPoint)->Bool)->[CGPoint] {
        let unit:CGFloat=12, stride=200, nodeLimit=30000
        func key(_ p:CGPoint)->Int {Int((p.y/unit).rounded())*stride+Int((p.x/unit).rounded())}
        func point(_ k:Int)->CGPoint {CGPoint(x:CGFloat(k%stride)*unit,y:CGFloat(k/stride)*unit)}
        func clear(_ a:CGPoint,_ b:CGPoint)->Bool {
            let count=max(1,Int(ceil(hypot(b.x-a.x,b.y-a.y)/3)))
            return (0...count).allSatisfy { n in
                let t=CGFloat(n)/CGFloat(count)
                return walkable(CGPoint(x:a.x+(b.x-a.x)*t,y:a.y+(b.y-a.y)*t))
            }
        }
        func nearest(_ p:CGPoint)->Int? {
            let center=key(p)
            return (-2...2).flatMap {dy in (-2...2).map {center+dy*stride+$0}}
                .filter {clear(p,point($0))}
                .min {point($0).distance(to:p)<point($1).distance(to:p)}
        }
        guard walkable(start),walkable(end),let a=nearest(start),let b=nearest(end) else {return []}
        var queue=[a],index=0,previous=[a:a]
        while index<queue.count && queue.count<nodeLimit {
            let current=queue[index];index += 1
            if current==b {
                var result=[end],k=b
                while k != a {result.append(point(k));k=previous[k]!}
                result.append(point(a))
                return result.reversed()
            }
            for next in [current-1,current+1,current-stride,current+stride] where previous[next]==nil {
                let p=point(next)
                if p.x>=0 && p.x<2200 && p.y>=0 && p.y<1600 && clear(point(current),p) {
                    previous[next]=current;queue.append(next)
                }
            }
        }
        return []
    }
}
