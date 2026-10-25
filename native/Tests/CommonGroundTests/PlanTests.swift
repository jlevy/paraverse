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

    @MainActor func testRankingEditsInvalidateVisibleAndRestoredPlans() throws {
        let suite = "PlanIdentity." + UUID().uuidString
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let planner = Planner(); planner.storage = defaults
        var profile = AttendeeProfile(); profile.name = "Example"; profile.title = "Engineer"; profile.background = "Databases"; profile.interests = ["Tools"]
        planner.updateProfile(profile)
        planner.sessions = [sampleSession()]; planner.hasPlan = true; planner.persistPlan()
        var edited = profile; edited.title = "Designer"; edited.background = "Interfaces"
        planner.updateProfile(edited)
        XCTAssertTrue(planner.sessions.isEmpty)
        XCTAssertFalse(planner.hasPlan)
        let restored = Planner(); restored.storage = defaults; restored.start(for: edited)
        XCTAssertTrue(restored.sessions.isEmpty)
        let original = Planner(); original.storage = defaults; original.start(for: profile)
        XCTAssertEqual(original.sessions.map(\.id), ["old"])
    }

    @MainActor func testProfileEditAcrossAwaitCannotPublishOrClearNewRequest() async throws {
        let planner = Planner()
        var first: CheckedContinuation<(Data, URLResponse), Error>?
        var second: CheckedContinuation<(Data, URLResponse), Error>?
        var count = 0
        planner.requestData = { _ in
            count += 1
            return try await withCheckedThrowingContinuation { continuation in
                if count == 1 { first = continuation } else { second = continuation }
            }
        }
        planner.generate()
        for _ in 0..<100 where first == nil { try await Task.sleep(for: .milliseconds(10)) }
        var edited = AttendeeProfile(); edited.background = "A different ranking profile"
        planner.updateProfile(edited)
        planner.generate()
        for _ in 0..<100 where second == nil { try await Task.sleep(for: .milliseconds(10)) }
        let response = HTTPURLResponse(url: URL(string: "http://127.0.0.1:8765/session-plan")!, statusCode: 200, httpVersion: nil, headerFields: nil)!
        let data = try JSONSerialization.data(withJSONObject: ["sessions": [["id": "old", "title": "Old", "speakers": "Example", "start": "2026-10-28T10:00:00-07:00", "end": "2026-10-28T11:00:00-07:00", "location": "Room", "sourceURL": "https://example.org/session", "reason": "Old ranking"]], "message": "Ready", "calendarChecked": false])
        first?.resume(returning: (data, response))
        try await Task.sleep(for: .milliseconds(30))
        XCTAssertTrue(planner.busy, "The old completion must not clear the new request's loading state")
        XCTAssertTrue(planner.sessions.isEmpty)
        second?.resume(returning: (Data(#"{"sessions":[],"message":"Ready","calendarChecked":false}"#.utf8), response))
        for _ in 0..<100 where planner.busy { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertFalse(planner.busy)
        planner.reset()
    }

    @MainActor func testExternalRefreshCarriesLateArrival() async throws {
        let suite = "LateRefresh.\(UUID())"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let planner = Planner(); planner.storage = defaults; planner.late = true
        var requestedLate: Bool?
        planner.requestData = { request in
            let body = try XCTUnwrap(JSONSerialization.jsonObject(with: request.httpBody!) as? [String: Any])
            requestedLate = body["late"] as? Bool
            let response = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
            return (Data(#"{"sessions":[],"message":"Ready","calendarChecked":false}"#.utf8), response)
        }
        planner.refreshExternalEvents()
        for _ in 0..<100 where planner.busy { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertFalse(planner.busy)
        XCTAssertEqual(requestedLate, true)
        planner.reset()
    }

    private func sampleSession() -> PlannedSession {
        PlannedSession(id: "old", title: "Old", speakers: "Example", start: "2026-10-28T10:00:00-07:00", end: "2026-10-28T11:00:00-07:00", location: "Room", sourceURL: "https://example.org/session", reason: "Old ranking")
    }
}
