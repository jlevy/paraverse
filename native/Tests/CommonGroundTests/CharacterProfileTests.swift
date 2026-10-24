import XCTest
@testable import CommonGround

final class CharacterProfileTests: XCTestCase {
    func testSatyamHasSourceBackedSectionsAndKeepsHisSpriteIdentity() throws {
        let profile = try XCTUnwrap(CharacterProfile.find("ptc-judge:satyam-singh"))
        XCTAssertEqual(profile.sections.count, 7)
        XCTAssertFalse(profile.reviewProvenance.model.isEmpty)
        XCTAssertEqual(profile.reviewProvenance.inputSha256.count, 64)
        XCTAssertTrue(profile.reviewProvenance.inputSha256.allSatisfy { $0.isHexDigit })
        XCTAssertEqual(profile.reviewProvenance.sourceRevision.count, 40)
        XCTAssertTrue(WorldSpeaker.directoryPeople.contains { $0.id == profile.personID })
        XCTAssertTrue(WorldCharacter.all.contains { $0.personID == profile.personID })
        for section in profile.sections {
            XCTAssertFalse(section.body.isEmpty)
            XCTAssertFalse(section.sources.isEmpty, section.title)
            XCTAssertTrue(section.sources.allSatisfy { $0.url.scheme == "https" })
        }
        XCTAssertTrue(profile.sections.contains { $0.body.contains("Global Connection Award") })
        XCTAssertNil(CharacterProfile.find("unknown-person"))
    }
}
