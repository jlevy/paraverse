import XCTest
@testable import CommonGround

final class CachedPeopleReviewProbeTests: XCTestCase {
    @MainActor func testCompleteAThenSessionsOnlyBThenCompleteBRefreshesPeople() async throws {
        let planner = Planner()
        let suite = "PR15Review." + UUID().uuidString
        planner.storage = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { planner.reset(); planner.storage.removePersistentDomain(forName: suite) }
        var plannedID = "A"
        var peopleRequests = 0
        planner.requestData = { request in
            let body = try XCTUnwrap(JSONSerialization.jsonObject(with: request.httpBody!) as? [String: Any])
            let response = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
            let result: [String: Any]
            if request.url!.path == "/chat" {
                peopleRequests += 1
                let people = (0..<10).map { index in
                    ["personID": "\(plannedID)-\(index)", "name": "Synthetic person", "role": "Engineer", "reason": "Matches plan \(plannedID)", "profileURL": "https://example.com/profile", "sourceURL": "https://example.com/source"]
                }
                result = ["action": "answer", "message": "People ready", "recommendations": people]
            } else if body["external"] as? Bool == true {
                result = ["sessions": [], "message": "No external events", "calendarChecked": false]
            } else {
                let session = ["id": plannedID, "title": "Synthetic session", "speakers": "Synthetic speaker", "start": "2026-10-28T10:00:00-07:00", "end": "2026-10-28T11:00:00-07:00", "location": "Stage", "sourceURL": "https://example.com/session", "reason": "Matches request"]
                result = ["sessions": [session], "message": "Plan ready", "calendarChecked": false]
            }
            return (try JSONSerialization.data(withJSONObject: result), response)
        }

        planner.generate(completePlan: true)
        try await waitUntilReady(planner)
        XCTAssertEqual(peopleRequests, 1)
        XCTAssertTrue(planner.peopleToMeet.allSatisfy { $0.personID.hasPrefix("A-") })

        plannedID = "B"
        planner.generate(completePlan: false)
        try await waitUntilReady(planner)
        XCTAssertEqual(planner.sessions.map(\.id), ["B"])
        XCTAssertEqual(peopleRequests, 1)

        planner.generate(completePlan: true)
        try await waitUntilReady(planner)
        XCTAssertEqual(peopleRequests, 2, "Complete plan B must refresh people generated for A")
        XCTAssertTrue(planner.peopleToMeet.allSatisfy { $0.personID.hasPrefix("B-") }, "People must correspond to the current complete plan")
    }

    @MainActor private func waitUntilReady(_ planner: Planner) async throws {
        for _ in 0..<500 where planner.busy { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertFalse(planner.busy)
    }
}
