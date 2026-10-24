import XCTest
@testable import CommonGround
final class PlanTests: XCTestCase {
    func testSessionDatesRespectPacificTime() throws {
        let json = """
        {"id":"real-session","title":"Database talk","speakers":"Speaker","start":"2026-10-28T16:30:00-07:00","end":"2026-10-28T17:30:00-07:00","location":"Room","sourceURL":"https://githubuniverse.com/","reason":"Matches databases"}
        """
        let session = try JSONDecoder().decode(PlannedSession.self, from: Data(json.utf8))
        XCTAssertEqual(session.day, "2026-10-28")
        XCTAssertEqual(session.endDate.timeIntervalSince(session.startDate), 3600)
        XCTAssertEqual(ISO8601DateFormatter().string(from: session.endDate), "2026-10-29T00:30:00Z")
    }
}
