import XCTest
@testable import CommonGround

final class RecommendationAvatarTests: XCTestCase {
    @MainActor func testRecommendedSpeakerSpritesLoad() {
        let names = ["Maggie Appleton", "Idan Gazit", "Janice Niemeir", "Ayman Bagabas", "William Woodruff", "Pamela Fox", "Erin Mikail Staples", "Julia Kasper"]
        for name in names {
            guard let speaker = WorldSpeaker.all.first(where: { $0.name == name }) else {
                XCTFail("Missing speaker: \(name)"); continue
            }
            XCTAssertNotNil(WorldCharacter.recommendationImage(for: speaker.id), name)
        }
    }
    @MainActor func testRecommendationIDsResolveToTheirOwnSprites() {
        for character in WorldCharacter.all where character.roles.contains("attendee") {
            let backendID = character.personID.replacingOccurrences(of: "attendee:", with: "").lowercased()
            let image = WorldCharacter.recommendationImage(for: backendID)
            XCTAssertNotNil(image, backendID)
            XCTAssertTrue(image === WorldCharacter.image(for: character.personID), backendID)
        }
        XCTAssertNotNil(WorldCharacter.recommendationImage(for: "orenme"))
        XCTAssertNil(WorldCharacter.recommendationImage(for: "unknown-attendee"))
    }
}
