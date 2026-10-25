import XCTest
@testable import CommonGround

final class CompletePlanTests: XCTestCase {
    @MainActor func testPeopleAndEventsLoadConcurrently() async throws {
        let planner = Planner()
        let suite = "CompletePlanTests." + UUID().uuidString
        planner.storage = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { planner.storage.removePersistentDomain(forName: suite) }
        var externalStarted = false
        planner.requestData = { request in
            let body = try XCTUnwrap(JSONSerialization.jsonObject(with: request.httpBody!) as? [String: Any])
            let response = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
            if request.url!.path == "/chat" {
                for _ in 0..<50 where !externalStarted { try await Task.sleep(for: .milliseconds(10)) }
                XCTAssertTrue(externalStarted, "External lookup must start before people lookup finishes")
                return (Data("{\"action\":\"answer\",\"message\":\"Ready\",\"recommendations\":[]}".utf8), response)
            }
            if body["external"] as? Bool == true { externalStarted = true }
            return (Data("{\"sessions\":[],\"message\":\"Ready\",\"calendarChecked\":false}".utf8), response)
        }
        planner.generate(completePlan: true)
        for _ in 0..<300 where planner.busy { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertFalse(planner.busy)
        XCTAssertTrue(planner.recommendationWarnings.isEmpty)
    }

    @MainActor func testUnchangedPlanReusesPeopleMatches() async throws {
        let planner = Planner()
        let suite = "CompletePlanTests." + UUID().uuidString
        planner.storage = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { planner.storage.removePersistentDomain(forName: suite) }
        planner.peopleToMeet = (0..<10).map { PersonRecommendation(personID: "p\($0)", name: "Person", role: "Engineer", reason: "Fit", profileURL: "https://example.com", sourceURL: "https://example.com", avatarAsset: nil) }
        planner.requestData = { request in
            XCTAssertNotEqual(request.url!.path, "/chat", "Unchanged matches should not need another people request")
            return (Data("{\"sessions\":[],\"message\":\"Ready\",\"calendarChecked\":false}".utf8), HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
        }
        planner.generate(completePlan: true)
        for _ in 0..<300 where planner.busy { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertEqual(planner.peopleToMeet.count, 10)
        XCTAssertFalse(planner.busy)
    }

    @MainActor func testSessionFailureEndsLoadingWithoutOpeningPlan() async throws {
        let planner = Planner()
        planner.requestData = { _ in throw URLError(.cannotConnectToHost) }
        planner.generate(completePlan: true)
        XCTAssertTrue(planner.generatingRecommendations)
        for _ in 0..<800 where planner.busy { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertFalse(planner.busy)
        XCTAssertFalse(planner.generatingRecommendations)
        XCTAssertFalse(planner.showPlan)
        XCTAssertTrue(planner.messages.last?.text.contains("couldn’t load") == true)
    }

    @MainActor func testOptionalSectionFailurePreservesSessionsAndExplainsMissingResults() async throws {
        let planner = Planner()
        let suite = "CompletePlanTests." + UUID().uuidString
        planner.storage = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { planner.storage.removePersistentDomain(forName: suite) }
        planner.requestData = { request in
            let body = try XCTUnwrap(JSONSerialization.jsonObject(with: request.httpBody!) as? [String: Any])
            if request.url!.path == "/chat" || body["external"] as? Bool == true { throw URLError(.timedOut) }
            let result: [String: Any] = ["sessions": [["id": "talk", "title": "AI", "speakers": "Speaker", "start": "2026-10-28T10:00:00-07:00", "end": "2026-10-28T11:00:00-07:00", "location": "Stage", "sourceURL": "https://githubuniverse.com", "reason": "Matches interests"]], "message": "Ready", "calendarChecked": false]
            return (try JSONSerialization.data(withJSONObject: result), HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
        }
        planner.generate(completePlan: true)
        for _ in 0..<800 where planner.busy { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertFalse(planner.busy)
        XCTAssertFalse(planner.generatingRecommendations)
        XCTAssertEqual(planner.recommendationWarnings.count, 2)
        XCTAssertEqual(planner.sessions.count, 1)
        XCTAssertTrue(planner.hasPlan)
        XCTAssertTrue(planner.messages.last?.text.contains("People recommendations couldn’t load") == true)
        XCTAssertTrue(planner.messages.last?.text.contains("External events couldn’t load") == true)
    }

    @MainActor func testTransientConnectionFailureRetriesWithoutLosingSavedSections() async throws {
        let planner = Planner()
        let suite = "CompletePlanTests." + UUID().uuidString
        planner.storage = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { planner.storage.removePersistentDomain(forName: suite) }
        let person = PersonRecommendation(personID: "saved", name: "Saved Person", role: "Engineer", reason: "Specific fit", profileURL: "https://example.com", sourceURL: "https://example.com", avatarAsset: nil)
        planner.peopleToMeet = [person]
        let savedEvent = PlannedSession(id: "saved-event", title: "Event", speakers: "Host", start: "2026-10-28T18:00:00-07:00", end: "2026-10-28T19:00:00-07:00", location: "SF", sourceURL: "https://example.com", reason: "Specific fit")
        planner.sideEvents = [savedEvent]
        var sessionAttempts = 0
        planner.requestData = { request in
            let body = try XCTUnwrap(JSONSerialization.jsonObject(with: request.httpBody!) as? [String: Any])
            if request.url!.path == "/chat" || body["external"] as? Bool == true { throw URLError(.cannotConnectToHost) }
            sessionAttempts += 1
            if sessionAttempts == 1 { throw URLError(.networkConnectionLost) }
            return (Data("{\"sessions\":[],\"message\":\"Ready\",\"calendarChecked\":false}".utf8), HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
        }
        planner.generate(completePlan: true)
        for _ in 0..<1000 where planner.busy { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertFalse(planner.busy)
        XCTAssertEqual(sessionAttempts, 2)
        XCTAssertEqual(planner.peopleToMeet.map(\.personID), ["saved"])
        XCTAssertEqual(planner.sideEvents.map(\.id), ["saved-event"])
        XCTAssertEqual(planner.recommendationWarnings.count, 2)
        XCTAssertTrue(planner.recommendationWarnings.allSatisfy { $0.contains("Showing your saved") })
        let stored = try XCTUnwrap(planner.storage.data(forKey: "lastPlanPeople"))
        XCTAssertEqual(try JSONDecoder().decode([PersonRecommendation].self, from: stored).count, 1)
    }

    @MainActor func testExternalRecoveryRetries503AndClearsOnlyItsWarning() async throws {
        let planner = Planner()
        let suite = "CompletePlanTests." + UUID().uuidString
        planner.storage = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { planner.storage.removePersistentDomain(forName: suite) }
        planner.recommendationWarnings = ["People recommendations couldn’t load. Try again.", "External events couldn’t load. Try again."]
        var attempts = 0
        planner.requestData = { request in
            attempts += 1
            return (Data("{\"sessions\":[],\"message\":\"Ready\",\"calendarChecked\":false}".utf8), HTTPURLResponse(url: request.url!, statusCode: attempts == 1 ? 503 : 200, httpVersion: nil, headerFields: nil)!)
        }
        planner.refreshExternalEvents()
        for _ in 0..<500 where planner.busy { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertEqual(attempts, 2)
        XCTAssertEqual(planner.recommendationWarnings, ["People recommendations couldn’t load. Try again."])
    }

    @MainActor func testCompletePlanGathersAllSectionsAndPassesSessionConflicts() async throws {
        let planner = Planner()
        let suite = "CompletePlanTests." + UUID().uuidString
        planner.storage = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { planner.storage.removePersistentDomain(forName: suite) }
        var calls: [String] = []
        let session: [String: Any] = ["id": "talk", "title": "AI tools", "speakers": "Speaker", "start": "2026-10-28T10:00:00-07:00", "end": "2026-10-28T11:00:00-07:00", "location": "Stage", "sourceURL": "https://githubuniverse.com", "reason": "Matches your interests"]
        planner.requestData = { request in
            XCTAssertTrue(planner.generatingRecommendations)
            XCTAssertFalse(planner.showPlan, "Do not reveal a partial plan while requests are pending")
            let body = try XCTUnwrap(JSONSerialization.jsonObject(with: request.httpBody!) as? [String: Any])
            let isExternal = body["external"] as? Bool == true
            let path = request.url!.path
            calls.append(isExternal ? "external" : path)
            let result: [String: Any]
            if path == "/chat" {
                result = ["action": "answer", "message": "Meet this person", "recommendations": [["personID": "person", "name": "Alex", "role": "Engineer", "reason": "Shared interests", "profileURL": "https://example.com", "sourceURL": "https://example.com"]]]
            } else {
                var item = session
                if isExternal {
                    let occupied = try XCTUnwrap(body["busy"] as? [[String: String]])
                    XCTAssertTrue(occupied.contains { $0["start"] == session["start"] as? String && $0["end"] == session["end"] as? String })
                    item["id"] = "side-event"
                    item["start"] = "2026-10-28T18:00:00-07:00"
                    item["end"] = "2026-10-28T19:00:00-07:00"
                }
                result = ["sessions": [item], "message": "Ready", "calendarChecked": false]
            }
            return (try JSONSerialization.data(withJSONObject: result), HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
        }
        let started = ContinuousClock.now
        planner.generate(completePlan: true)
        for _ in 0..<800 where planner.busy { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertFalse(planner.busy)
        XCTAssertGreaterThanOrEqual(started.duration(to: .now), .milliseconds(750))
        XCTAssertLessThan(started.duration(to: .now), .seconds(2))
        XCTAssertEqual(calls, ["/session-plan", "/chat", "external"])
        XCTAssertEqual(planner.sessions.count, 1)
        XCTAssertEqual(planner.peopleToMeet.count, 1)
        XCTAssertEqual(planner.sideEvents.count, 1)
        XCTAssertFalse(planner.generatingRecommendations)
        XCTAssertTrue(planner.recommendationWarnings.isEmpty)
        XCTAssertTrue(planner.showPlan)
    }

    @MainActor func testOpeningCompletePlanWhileBusyDoesNotReplaceActiveWork() {
        let planner = Planner()
        planner.busy = true
        planner.generatingRecommendations = true
        planner.status = "Loading the current plan"
        planner.requestData = { _ in
            XCTFail("Opening planning while busy must not start a second request")
            throw URLError(.cancelled)
        }
        planner.generate(completePlan: true)
        XCTAssertTrue(planner.busy)
        XCTAssertTrue(planner.generatingRecommendations)
        XCTAssertEqual(planner.status, "Loading the current plan")
    }
}
