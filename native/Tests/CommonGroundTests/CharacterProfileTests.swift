import XCTest
@testable import CommonGround

final class CharacterProfileTests: XCTestCase {
    func testSatyamSearchAcceptsPastedBullets() throws {
        let person = try XCTUnwrap(WorldSpeaker.directoryPeople.first { $0.id == "ptc-judge:satyam-singh" })
        for query in ["Satyam", "Satyam Singh", "* Satyam Singh", "• Satyam Singh", "  - Satyam Singh  "] {
            XCTAssertTrue(person.matchesDirectorySearch(query), query)
        }
        XCTAssertFalse(person.matchesDirectorySearch("nonexistent person"))
    }

    func testSatyamHasSourceBackedSectionsAndKeepsHisSpriteIdentity() throws {
        let profile = try XCTUnwrap(CharacterProfile.find("ptc-judge:satyam-singh"))
        XCTAssertEqual(profile.sections.count, 7)
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
