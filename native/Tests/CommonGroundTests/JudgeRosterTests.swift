import XCTest
@testable import CommonGround

final class JudgeRosterTests: XCTestCase {
    func testJudgesAreSearchableWithoutBeingUniverseSpeakers() {
        let judges = WorldSpeaker.judges
        XCTAssertEqual(judges.count, 10)
        XCTAssertEqual(Set(judges.map(\.id)).count, 10)
        let directoryIDs = Set(WorldSpeaker.directoryPeople.map(\.id))
        let speakerIDs = Set(WorldSpeaker.all.map(\.id))
        for judge in judges {
            XCTAssertTrue(judge.isJudge)
            XCTAssertTrue(directoryIDs.contains(judge.id), judge.name)
            XCTAssertFalse(speakerIDs.contains(judge.id), judge.name)
            XCTAssertTrue(judge.sessions.isEmpty)
            XCTAssertEqual(judge.sourceURL, "https://www.wemakedevs.org/hackathons/ptc/judges")
        }
    }

    @MainActor func testEveryJudgeHasAnExplicitBundledAvatar() throws {
        for judge in WorldSpeaker.judges {
            let character = try XCTUnwrap(WorldCharacter.all.first { $0.personID == judge.id })
            XCTAssertTrue(character.roles.contains("judge"))
            XCTAssertNotNil(WorldCharacter.recommendationImage(for: judge.id), judge.name)
            if judge.avatarNote != nil {
                XCTAssertEqual(character.sprite, "judges-1.png")
                XCTAssertEqual(character.atlasCell, 3)
            }
        }
        XCTAssertEqual(WorldSpeaker.judges.filter { $0.avatarNote != nil }.count, 3)
    }
}
