import XCTest
import AppKit
import SpriteKit
@testable import CommonGround

final class HallNavigationTests: XCTestCase {
    func testRouteGoesAroundFurniture() {
        let obstacle = CGRect(x:80,y:0,width:50,height:150)
        let valid: (CGPoint)->Bool = { $0.x>=0 && $0.x<=240 && $0.y>=0 && $0.y<=240 && !obstacle.contains($0) }
        let route = HallNavigation.route(from:CGPoint(x:24,y:48),to:CGPoint(x:192,y:48),walkable:valid)
        XCTAssertFalse(route.isEmpty)
        XCTAssertTrue(route.allSatisfy(valid))
        XCTAssertTrue(route.contains{ $0.y>=150 })
        XCTAssertEqual(route.last,CGPoint(x:192,y:48))
    }
    func testBlockedDestinationIsRejected() {
        XCTAssertTrue(HallNavigation.route(from:.zero,to:CGPoint(x:100,y:100),walkable:{$0.x<50}).isEmpty)
    }
    func testDisconnectedDestinationIsRejected() {
        XCTAssertTrue(HallNavigation.route(from:CGPoint(x:24,y:48),to:CGPoint(x:192,y:48),walkable:{$0.x>=0 && $0.x<=240 && $0.y>=0 && $0.y<=240 && !($0.x>70 && $0.x<150)}).isEmpty)
    }
    func testEveryCommonsSpaceReachableFromEntrance() {
        for space in CommonsLayout.spaces {
            XCTAssertTrue(CommonsLayout.walkable(space.point), space.title)
            let route = HallNavigation.route(from: CommonsLayout.entrance, to: space.point, walkable: CommonsLayout.walkable)
            XCTAssertFalse(route.isEmpty, "Unreachable: " + space.title)
            XCTAssertTrue(route.allSatisfy(CommonsLayout.walkable), space.title)
        }
    }
    func testStageAndSponsorCountersAreNotWalkable() {
        for p in [CommonsLayout.point(460,75), CommonsLayout.point(260,210), CommonsLayout.point(455,420)] {
            XCTAssertFalse(CommonsLayout.walkable(p))
        }
    }
    @MainActor func testSceneSpeakerSelectionZoomAndWalking() async {
        let scene = ConferenceScene(size: CGSize(width:1000,height:650))
        scene.build()
        var selectedID: String?
        scene.selectSpeaker = { selectedID = $0.id }
        var target = scene.speakerPositions[WorldSpeaker.all[0].id]!; target.y += 20
        scene.clicked(target)
        XCTAssertEqual(selectedID, WorldCharacter.all.first?.personID)
        scene.zoomTo(0.6)
        XCTAssertEqual(scene.cameraNode.xScale,0.6,accuracy:0.001)
        let start = scene.player.position
        scene.keys.insert(13)
        for frame in 1...20 { scene.update(Double(frame)/60) }
        scene.keys.removeAll()
        XCTAssertGreaterThan(scene.player.position.y,start.y)
        XCTAssertTrue(scene.walkable(scene.player.position))
    }
    func testSpawnsUseClearFloorOutsideDoorways() {
        let crowd=ConferenceCrowd(count:183)
        XCTAssertEqual(crowd.walkers.count,183)
        for person in crowd.walkers { XCTAssertTrue(CommonsLayout.isActivitySpot(person.position)) }
        for i in crowd.walkers.indices { for j in crowd.walkers.indices where j>i {
            XCTAssertGreaterThanOrEqual(crowd.walkers[i].position.distance(to:crowd.walkers[j].position),31.99)
        } }
    }

    func testCrowdKeepsMovingWithoutCrossingSolidsOrOverlapping() {
        var crowd=ConferenceCrowd(count:12)
        var travelers=Set<Int>(),activeSamples=[Int]()
        for frame in 0..<1200 {
            let before=crowd.walkers.map(\.position)
            crowd.update(dt:0.1)
            for i in crowd.walkers.indices {
                let person=crowd.walkers[i]
                XCTAssertTrue(crowd.graph.clearSegment(before[i],person.position))
                if person.distanceWalked>50 {travelers.insert(i)}
            }
            if frame%50 == 0 {
                let moving=crowd.walkers.filter {$0.speed>1}.count
                activeSamples.append(moving)
                XCTAssertLessThanOrEqual(crowd.walkers.filter(\.isWalking).count,ConferenceCrowd.maximumTravelers)
                for i in crowd.walkers.indices {for j in crowd.walkers.indices where j>i {
                    XCTAssertGreaterThanOrEqual(crowd.walkers[i].position.distance(to:crowd.walkers[j].position),21.99)
                }}
            }
        }
        XCTAssertGreaterThan(crowd.walkers.reduce(0) {$0+$1.completedTrips},10,"Trips must finish, not just accumulate movement while stuck")
        XCTAssertGreaterThan(travelers.count,6,"Crowd must circulate, not merely move once at startup")
        XCTAssertTrue(activeSamples.dropFirst(2).allSatisfy {$0>=1},"Visible movement must continue throughout the simulation")
        XCTAssertTrue(crowd.walkers.allSatisfy { !$0.activity.isEmpty }, "Every visible character needs an activity label")
    }

    @MainActor func testAmbientCrowdIsLimitedAndPauseStopsCrowd() async {
        let scene=ConferenceScene();scene.build()
        XCTAssertEqual(Set(scene.speakerPositions.keys),Set(WorldSpeaker.all.prefix(12).map(\.id)))
        XCTAssertTrue(Set(WorldSpeaker.all.map(\.id)).isSubset(of: Set(WorldSpeaker.directoryPeople.map(\.id))))
        let before=scene.speakerPositions
        scene.ambientPaused=true
        for frame in 1...60 { scene.update(Double(frame)/60) }
        XCTAssertEqual(before,scene.speakerPositions)
    }
    @MainActor func testSpriteFramesIgnoreTransparentNoiseAndKeepConstantHeight() throws {
        let scene = ConferenceScene()
        let body = SKSpriteNode()
        for row in 0..<4 { for column in 0..<3 {
            let image = try XCTUnwrap(NSImage(contentsOf: worldAsset("WorldArt/player-\(row)-\(column).png")))
            let texture = scene.characterTexture(image)
            scene.setPose(body, texture: texture)
            XCTAssertEqual(body.size.height, 44)
            XCTAssertLessThan(body.size.width, 28, "Invisible atlas pixels must not shift the visible character")
        } }
    }

    func testColumnsAndTheirClearanceAreBlocked() {
        // Landmarks are independent of the obstacle collection used by navigation.
        for (x,y) in [(207.0,130.0),(335,140),(593,150),(805,230),(198,130),(450,360)] {
            XCTAssertFalse(CommonsLayout.walkable(CommonsLayout.point(x,y)))
        }
    }

    func testVisibleFurnitureIsBlocked() {
        for rect in CommonsLayout.furnishings {
            XCTAssertFalse(CommonsLayout.walkable(CommonsLayout.point(rect.midX, rect.midY)))
        }
    }

    func testOfficialCatalogHasUniqueIDsAndPhotos() throws {
        let people = WorldSpeaker.all
        XCTAssertEqual(people.count,183)
        XCTAssertEqual(Set(people.map(\.id)).count,people.count)
        for person in people {
            XCTAssertFalse(person.name.isEmpty)
            XCTAssertTrue(person.sourceURL.hasPrefix("https://"))
            if let photo=person.photo { XCTAssertTrue(FileManager.default.fileExists(atPath:worldAsset("SpeakerPhotos/"+photo).path)) }
        }
    }
}
