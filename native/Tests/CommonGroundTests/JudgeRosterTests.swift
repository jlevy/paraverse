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
            XCTAssertTrue(judge.isJudge || judge.isHost)
            XCTAssertTrue(directoryIDs.contains(judge.id), judge.name)
            XCTAssertFalse(speakerIDs.contains(judge.id), judge.name)
            XCTAssertTrue(judge.sessions.isEmpty)
            XCTAssertTrue(judge.sourceURL.hasPrefix("https://"))
        }
    }

    @MainActor func testEveryJudgeHasAnExplicitBundledAvatar() throws {
        for judge in WorldSpeaker.judges.filter(\.isJudge) {
            let character = try XCTUnwrap(WorldCharacter.all.first { $0.personID == judge.id })
            XCTAssertTrue(character.roles.contains("judge"))
            XCTAssertNotNil(WorldCharacter.recommendationImage(for: judge.id), judge.name)
            if judge.avatarNote != nil {
                XCTAssertEqual(character.sprite, "judges-1.png")
                XCTAssertEqual(character.atlasCell, 3)
            }
        }
        XCTAssertEqual(WorldSpeaker.judges.filter(\.isJudge).count, 9)
        XCTAssertEqual(WorldSpeaker.judges.filter(\.isHost).count, 1)
    }

    func testDirectorySearchAndSummariesPreserveJudgeAndHostRoles() throws {
        for judge in WorldSpeaker.judges.filter(\.isJudge) {
            XCTAssertTrue(judge.matchesDirectorySearch("judges"), judge.name)
            XCTAssertTrue(judge.matchesDirectorySearch("  JUDGES  "), judge.name)
            XCTAssertTrue(judge.matchesDirectorySearch(judge.name), judge.name)
            XCTAssertEqual(judge.directorySummary, [judge.company, "Patch the Conference"].filter { !$0.isEmpty }.joined(separator: " · "))
        }
        let host = try XCTUnwrap(WorldSpeaker.judges.first(where: \.isHost))
        XCTAssertFalse(host.isJudge)
        XCTAssertTrue(host.matchesDirectorySearch("hosts"))
        XCTAssertTrue(host.directorySummary.contains("Host"))
        XCTAssertEqual(host.participationLabel, "Host")
        XCTAssertTrue(WorldSpeaker.directoryPeople.allSatisfy { $0.matchesDirectorySearch("  ") })
    }

    func testPlaceholderJudgeCardsFollowOtherDirectoryPeople() throws {
        let people = WorldSpeaker.directoryPeople
        let firstPlaceholder = try XCTUnwrap(people.firstIndex { $0.isJudge && $0.avatarNote != nil })
        XCTAssertTrue(people[..<firstPlaceholder].allSatisfy { !($0.isJudge && $0.avatarNote != nil) })
        XCTAssertTrue(people[firstPlaceholder...].allSatisfy { $0.isJudge && $0.avatarNote != nil })
        XCTAssertEqual(Set(people.map(\.id)), Set((WorldSpeaker.all + WorldSpeaker.judges).map(\.id)))
    }
}
