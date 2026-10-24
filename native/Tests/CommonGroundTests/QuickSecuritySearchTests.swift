import XCTest
@testable import CommonGround

final class QuickSecuritySearchTests: XCTestCase {
    func testFirstDaySecuritySearchUsesCatalog() throws {
        let results = try XCTUnwrap(CompanionReply.quickSecuritySearch("Find me security sessions on the first day of GitHub Universe."))
        XCTAssertFalse(results.isEmpty)
        XCTAssertTrue(results.allSatisfy { $0.day == "2026-10-28" })
        XCTAssertEqual(results.map(\.start), results.map(\.start).sorted())
        XCTAssertNil(CompanionReply.quickSecuritySearch("Find me security sessions on the second day of GitHub Universe."))
        XCTAssertNil(CompanionReply.quickSecuritySearch("Find me security sessions on the first day of GitHub Universe after 3 PM."))
    }
}
