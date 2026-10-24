import XCTest
@testable import ParaverseGraphClient

/// Decodes responses captured from `paraverse-graph query ... --format json`.
final class GraphClientTests: XCTestCase {
    private func fixture(_ name: String) throws -> QueryResult {
        let url = try XCTUnwrap(Bundle.module.url(forResource: name, withExtension: "json", subdirectory: "Fixtures"))
        return try JSONDecoder().decode(QueryResult.self, from: Data(contentsOf: url))
    }

    func testPersonCardDecodesAsAGraph() throws {
        let result = try fixture("person_card")
        let person = try XCTUnwrap(result.graph.nodes.first { $0.id == "person:april-leonard" })
        XCTAssertTrue(person.labels.contains("Speaker"))
        let sessions = result.graph.links.filter { $0.relationship == "PRESENTS" }.map(\.target)
        XCTAssertFalse(sessions.isEmpty)
        XCTAssertTrue(sessions.allSatisfy { $0.hasPrefix("session:") })
    }

    func testScheduleRowsDecodeAsRecords() throws {
        let records = try fixture("schedule").records
        XCTAssertEqual(records.first?["title"]?.string, "Opening Keynote")
        XCTAssertFalse(records.first?["speakers"]?.array?.isEmpty ?? true)
        let starts = records.compactMap { $0["start_epoch"]?.number }
        XCTAssertEqual(starts, starts.sorted())
    }

    func testConnectingPathsReferenceGraphNodes() throws {
        let result = try fixture("connecting_paths")
        let ids = Set(result.graph.nodes.map(\.id))
        for row in result.rows {
            let path = try XCTUnwrap(row.first?.object?["nodes"]?.array?.compactMap(\.string))
            XCTAssertEqual(path.first, "person:april-leonard")
            XCTAssertEqual(path.last, "org:jfrog")
            XCTAssertTrue(Set(path).isSubset(of: ids))
        }
    }

    func testEntityCarriesTheSoftschemaPayload() throws {
        let node = try XCTUnwrap(try fixture("entity").graph.nodes.first)
        XCTAssertEqual(node.doc?["id"]?.string, "org:jfrog")
        XCTAssertEqual(node.doc?["sponsorship"]?.object?["tier"]?.string, "platinum")
    }
}
