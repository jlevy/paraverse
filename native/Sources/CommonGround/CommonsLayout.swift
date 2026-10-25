import Foundation
import CoreGraphics

// Map coordinates use a 1000 × 500 artboard, origin at the image's top left.
// Shared by navigation, camera destinations and character placement.
enum CommonsLayout {
    struct Space: Identifiable {
        let id: String
        let title: String
        let x, y: CGFloat
        var point: CGPoint { CommonsLayout.point(x,y) }
    }
    static let spaces: [Space] = [
        .init(id:"commons",title:"Connected commons",x:470,y:335),
        .init(id:"sponsors",title:"Sponsor neighborhood",x:205,y:250),
        .init(id:"stage",title:"Main stage",x:460,y:158),
        .init(id:"library",title:"Open source library",x:155,y:130),
        .init(id:"mentoring",title:"Contributor mentoring",x:308,y:145),
        .init(id:"coffee",title:"Coffee & conversations",x:932,y:125),
        .init(id:"discussions",title:"Discussion lounge",x:730,y:264),
        .init(id:"hackathon",title:"Hackathon studio",x:830,y:285),
        .init(id:"workshop",title:"Workshop & robotics",x:630,y:354),
        .init(id:"judging",title:"Demo & judging theater",x:855,y:440),
        .init(id:"arcade",title:"Arcade recess",x:255,y:447),
        .init(id:"podcast",title:"Podcast studio",x:130,y:446),
        .init(id:"quiet",title:"Quiet recharge",x:748,y:455)
    ]
    static func point(_ x:CGFloat,_ y:CGFloat)->CGPoint { CGPoint(x:x*2.2,y:(500-y)*2.2) }
    static let entrance = point(450,452)
    // Coordinates are traced against the bundled illustration, in artboard units.
    // Wall openings below are drawn as doorways so the visual and physical maps agree.
    static let bodyRadius: CGFloat = 4
    static let floor = CGRect(x:18,y:26,width:964,height:438)
    static let doorways: [CGRect] = [
        CGRect(x:672,y:52,width:24,height:32),
        CGRect(x:610,y:363,width:28,height:20),
        CGRect(x:574,y:379,width:24,height:28),
        CGRect(x:684,y:441,width:22,height:24),
        CGRect(x:368,y:338,width:28,height:50),
        CGRect(x:546,y:338,width:28,height:50),
        CGRect(x:630,y:145,width:28,height:14),
        CGRect(x:744,y:145,width:28,height:14),
        CGRect(x:641,y:247,width:28,height:16),
        CGRect(x:790,y:270,width:30,height:36),
        CGRect(x:790,y:399,width:30,height:36),
        CGRect(x:671,y:367,width:28,height:16),
        CGRect(x:140,y:375,width:28,height:16),
        CGRect(x:226,y:375,width:28,height:16),
        CGRect(x:700,y:388,width:28,height:16),
    ]
    static let walls: [CGRect] = [
        CGRect(x:328,y:26,width:12,height:134),
        CGRect(x:328,y:228,width:12,height:47),
        CGRect(x:328,y:280,width:12,height:48),
        CGRect(x:328,y:388,width:12,height:60),
        CGRect(x:190,y:26,width:8,height:83),
        CGRect(x:676,y:26,width:12,height:119),
        CGRect(x:630,y:145,width:352,height:10),
        CGRect(x:630,y:153,width:12,height:105),
        CGRect(x:792,y:153,width:12,height:294),
        CGRect(x:809,y:208,width:173,height:9),
        CGRect(x:809,y:326,width:173,height:9),
        CGRect(x:641,y:247,width:151,height:10),
        CGRect(x:580,y:269,width:12,height:107),
        CGRect(x:592,y:367,width:200,height:12),
        CGRect(x:690,y:276,width:9,height:90),
        CGRect(x:580,y:388,width:12,height:68),
        CGRect(x:690,y:395,width:9,height:62),
        CGRect(x:18,y:375,width:310,height:10),
        CGRect(x:160,y:385,width:10,height:64),
        CGRect(x:190,y:385,width:10,height:64),
        CGRect(x:340,y:343,width:240,height:40),
        CGRect(x:350,y:353,width:13,height:42),
    ]
    static let columns: [CGRect] = [
        CGRect(x:201,y:108,width:13,height:45),
        CGRect(x:328,y:106,width:17,height:65),
        CGRect(x:360,y:129,width:11,height:42),
        CGRect(x:558,y:128,width:12,height:43),
        CGRect(x:585,y:116,width:19,height:57),
        CGRect(x:632,y:144,width:15,height:117),
        CGRect(x:678,y:119,width:17,height:44),
        CGRect(x:797,y:142,width:18,height:103),
        CGRect(x:797,y:252,width:18,height:124),
        CGRect(x:578,y:268,width:15,height:61),
        CGRect(x:797,y:384,width:17,height:63),
        CGRect(x:185,y:384,width:15,height:45),
    ]
    static let furniture: [CGRect] = [
        CGRect(x:366,y:26,width:191,height:125), // Stage and audience seating
        CGRect(x:556,y:176,width:56,height:72), // Billboard
        CGRect(x:390,y:384,width:150,height:34), // Registration
        CGRect(x:394,y:421,width:125,height:17), // Queue barriers
        CGRect(x:598,y:84,width:57,height:34),
        CGRect(x:570,y:42,width:77,height:31),
        CGRect(x:373,y:282,width:66,height:43),
        CGRect(x:501,y:283,width:49,height:41),
        CGRect(x:447,y:232,width:64,height:48),
        CGRect(x:363,y:215,width:63,height:50),
        CGRect(x:438,y:191,width:43,height:35),
        CGRect(x:397,y:167,width:37,height:31),
        CGRect(x:27,y:64,width:36,height:54),
        CGRect(x:69,y:68,width:36,height:48),
        CGRect(x:119,y:70,width:53,height:48),
        CGRect(x:62,y:42,width:124,height:21),
        CGRect(x:215,y:42,width:91,height:33),
        CGRect(x:232,y:109,width:62,height:27),
        CGRect(x:37,y:143,width:112,height:78), // Sponsor booths
        CGRect(x:214,y:170,width:99,height:58),
        CGRect(x:25,y:275,width:75,height:71),
        CGRect(x:119,y:275,width:68,height:70),
        CGRect(x:229,y:278,width:74,height:74),
        CGRect(x:68,y:230,width:62,height:44),
        CGRect(x:241,y:235,width:57,height:39),
        CGRect(x:24,y:346,width:71,height:29),
        CGRect(x:211,y:354,width:58,height:21),
        CGRect(x:767,y:62,width:108,height:39), // Coffee bar
        CGRect(x:700,y:86,width:49,height:26),
        CGRect(x:749,y:115,width:75,height:23),
        CGRect(x:839,y:113,width:67,height:24),
        CGRect(x:900,y:89,width:56,height:25),
        CGRect(x:895,y:59,width:43,height:22),
        CGRect(x:650,y:163,width:126,height:44), // Discussion boards and seats
        CGRect(x:665,y:211,width:109,height:33),
        CGRect(x:820,y:167,width:161,height:31),
        CGRect(x:846,y:238,width:131,height:20),
        CGRect(x:850,y:272,width:120,height:50),
        CGRect(x:603,y:307,width:83,height:32),
        CGRect(x:649,y:343,width:38,height:23),
        CGRect(x:745,y:342,width:41,height:25),
        CGRect(x:836,y:339,width:97,height:77),
        CGRect(x:949,y:394,width:33,height:30),
        CGRect(x:878,y:426,width:70,height:23),
        CGRect(x:601,y:403,width:76,height:46),
        CGRect(x:707,y:402,width:76,height:45),
        CGRect(x:206,y:396,width:95,height:37),
        CGRect(x:29,y:405,width:110,height:29),
    ]
    static let planters: [CGRect] = [
        CGRect(x:445,y:164,width:29,height:31),
        CGRect(x:511,y:163,width:20,height:27),
        CGRect(x:357,y:172,width:25,height:33),
        CGRect(x:332,y:176,width:20,height:30),
        CGRect(x:532,y:165,width:20,height:38),
        CGRect(x:535,y:292,width:19,height:33),
        CGRect(x:474,y:305,width:21,height:27),
        CGRect(x:265,y:131,width:32,height:24),
        CGRect(x:167,y:236,width:29,height:34),
        CGRect(x:190,y:318,width:25,height:40),
    ]
    static let furnishings = furniture + planters
    static let structure = walls + columns
    static let solidFootprints = structure + furnishings
    static let occlusionRects: [CGRect] = {
        var result = furnishings
        for wall in structure {
            var pieces = [wall]
            for door in doorways {
                pieces = pieces.flatMap { piece -> [CGRect] in
                    let cut = piece.intersection(door)
                    guard !cut.isNull else { return [piece] }
                    return [CGRect(x:piece.minX,y:piece.minY,width:piece.width,height:cut.minY-piece.minY),
                            CGRect(x:piece.minX,y:cut.maxY,width:piece.width,height:piece.maxY-cut.maxY),
                            CGRect(x:piece.minX,y:cut.minY,width:cut.minX-piece.minX,height:cut.height),
                            CGRect(x:cut.maxX,y:cut.minY,width:piece.maxX-cut.maxX,height:cut.height)]
                        .filter { $0.width > 0 && $0.height > 0 }
                }
            }
            result += pieces
        }
        return result
    }()

    static func walkable(_ p:CGPoint)->Bool {
        let a = CGPoint(x:p.x/2.2,y:500-p.y/2.2)
        guard floor.insetBy(dx:bodyRadius,dy:bodyRadius).contains(a) else { return false }
        if furnishings.contains(where: { $0.insetBy(dx:-bodyRadius,dy:-bodyRadius).contains(a) }) { return false }
        let inDoor = doorways.contains { door in
            let horizontal = door.width >= door.height || door.minY == 338
            return door.insetBy(dx:horizontal ? bodyRadius : -bodyRadius,
                                dy:horizontal ? -bodyRadius : bodyRadius).contains(a)
        }
        return inDoor || !structure.contains { $0.insetBy(dx:-bodyRadius,dy:-bodyRadius).contains(a) }
    }

    static func isActivitySpot(_ p: CGPoint) -> Bool {
        let a = CGPoint(x:p.x/2.2,y:500-p.y/2.2)
        return a.y > 65 && walkable(p) && !doorways.contains { $0.insetBy(dx:-20,dy:-20).contains(a) }
            && hypot(p.x-entrance.x,p.y-entrance.y) > 60
    }
}
