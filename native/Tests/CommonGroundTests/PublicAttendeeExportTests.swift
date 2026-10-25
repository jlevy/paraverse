import XCTest
@testable import CommonGround

final class PublicAttendeeExportTests: XCTestCase {
    func testEveryPublishedAttendanceRecordDecodesWithoutEnrichment() throws {
        let nativeRoot = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let data = try Data(contentsOf: nativeRoot.appendingPathComponent("Assets/universe-attendees.json"))
        let rows = try JSONDecoder().decode([PublicAttendee].self, from: data)
        let records = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [[String: Any]])
        let stableIDs = records.compactMap { $0["id"] as? String }
        XCTAssertEqual(stableIDs.count, 12)
        XCTAssertEqual(Set(stableIDs).count, 12)
        XCTAssertTrue(records.allSatisfy { ($0["attendance_status"] as? String)?.isEmpty == false })
        XCTAssertEqual(rows.count, 12)
        XCTAssertEqual(Set(rows.map(\.username)).count, rows.count)
        for row in rows {
            XCTAssertFalse(row.name.isEmpty)
            XCTAssertFalse(row.evidence.isEmpty)
            XCTAssertFalse(row.matching_opt_in)
            XCTAssertNil(row.role)
            XCTAssertNil(row.about)
            XCTAssertNil(row.interests)
            XCTAssertNil(row.linkedin_url)
            XCTAssertNil(row.github_url)
        }
    }
}
