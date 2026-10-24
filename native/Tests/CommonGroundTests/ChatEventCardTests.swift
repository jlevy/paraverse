import XCTest
@testable import CommonGround

final class ChatEventCardTests: XCTestCase {
    func testEventCardsUseCatalogDataAndRejectUnknownOrDuplicateIDs() throws {
        let reply = try JSONDecoder().decode(CompanionReply.self, from: Data(#"{"action":"answer","message":"Security sessions","sessionIDs":["unknown","security","security"]}"#.utf8))
        let event = PlannedSession(id: "security", title: "Security workshop", speakers: "Speaker", start: "2026-10-28T10:30:00-07:00", end: "2026-10-28T11:30:00-07:00", location: "Workshop", sourceURL: "https://example.com/session", reason: "")
        let cards = reply.eventCards(catalog: [event])
        XCTAssertEqual(cards.map(\.id), ["security"])
        XCTAssertEqual(cards.first?.title, event.title)
        XCTAssertEqual(cards.first?.sourceURL, event.sourceURL)
    }
    func testLiveSecurityResponseIDsResolveToDayOneCards() throws {
        let reply = try JSONDecoder().decode(CompanionReply.self, from: Data(#"{"action":"answer","message":"Security sessions","sessionIDs":["1777512208544001YnaL","1777658986177001QNCH","1777692373101001qvdo"]}"#.utf8))
        let cards = reply.eventCards()
        XCTAssertEqual(cards.count, 3)
        XCTAssertTrue(cards.allSatisfy { $0.day == "2026-10-28" })
    }
}
