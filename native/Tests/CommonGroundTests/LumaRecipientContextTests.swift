import XCTest
@testable import CommonGround

final class LumaRecipientContextTests: XCTestCase {
    private func person(_ id: String) -> PersonRecommendation {
        PersonRecommendation(personID: id, name: "Synthetic \(id)", role: "Engineer", reason: "Shared tools interest", profileURL: "https://example.org/\(id)", sourceURL: "https://example.org/public", avatarAsset: nil)
    }
    private func replyData() -> Data {
        Data(#"{"action":"answer","message":"Review this meetup","recommendations":[],"eventDraft":{"id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","title":"Synthetic meetup","description":"Review first","start":"2026-10-28T10:00:00-07:00","end":"2026-10-28T11:00:00-07:00","venueName":"Synthetic venue","address":"Synthetic public venue","venueReason":"Published hours","sourceURL":"https://example.org/venue","status":"draft","visibility":"private","demoEmail":""}}"#.utf8)
    }
    @MainActor func testDraftCapturesRecipientsBeforeAwaitAndInviteFollowupReusesThem() async throws {
        let planner = Planner()
        planner.peopleToMeet = [person("first")]
        var pending: CheckedContinuation<(Data, URLResponse), Error>?
        var requests = 0
        planner.requestData = { _ in
            requests += 1
            return try await withCheckedThrowingContinuation { pending = $0 }
        }
        planner.send("Arrange a meetup")
        for _ in 0..<100 where pending == nil { try await Task.sleep(for: .milliseconds(5)) }
        guard let pending else { planner.reset(); return XCTFail("Chat must use the mocked transport") }
        planner.peopleToMeet = [person("later")]
        let response = HTTPURLResponse(url: URL(string: "http://127.0.0.1:8765/chat")!, statusCode: 200, httpVersion: nil, headerFields: nil)!
        pending.resume(returning: (replyData(), response))
        for _ in 0..<100 where planner.busy { try await Task.sleep(for: .milliseconds(5)) }
        let original = try XCTUnwrap(planner.messages.last)
        // Constructing the card inspects its inputs without hosting its network tasks.
        XCTAssertEqual(try XCTUnwrap(original.meetupCard).people.map(\.id), ["first"])
        planner.send("Invite them")
        XCTAssertEqual(try XCTUnwrap(planner.messages.last?.meetupCard).people.map(\.id), ["first"])
        XCTAssertEqual(requests, 1, "Showing recipient review must not issue an invitation or another chat request")
        planner.reset()
    }
    @MainActor func testLatestChatRecommendationsBecomeNextDraftContext() async throws {
        let planner = Planner(); planner.peopleToMeet = [person("planned")]
        let recommendations = try JSONSerialization.jsonObject(with: JSONEncoder().encode([person("chat")]))
        var requests = 0
        planner.requestData = { request in
            requests += 1
            let data = requests == 1 ? try JSONSerialization.data(withJSONObject: ["action": "answer", "message": "Meet these people", "recommendations": recommendations]) : self.replyData()
            return (data, HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
        }
        planner.send("Who should I meet?")
        for _ in 0..<100 where planner.busy { try await Task.sleep(for: .milliseconds(5)) }
        planner.send("Arrange a meetup")
        for _ in 0..<100 where planner.busy { try await Task.sleep(for: .milliseconds(5)) }
        XCTAssertEqual(try XCTUnwrap(planner.messages.last?.meetupCard).people.map(\.id), ["chat"])
        XCTAssertEqual(planner.peopleToMeet.map(\.id), ["planned"], "Chat recipient context must not rewrite the saved plan")
        planner.reset()
    }
    @MainActor func testProfileChangeDiscardsPendingDraftAndRecipients() async throws {
        let planner = Planner(); planner.peopleToMeet = [person("old")]
        var pending: CheckedContinuation<(Data, URLResponse), Error>?
        planner.requestData = { _ in try await withCheckedThrowingContinuation { pending = $0 } }
        planner.send("Arrange a meetup")
        for _ in 0..<100 where pending == nil { try await Task.sleep(for: .milliseconds(5)) }
        guard let pending else { planner.reset(); return XCTFail("Chat must use the mocked transport") }
        var edited = AttendeeProfile(); edited.background = "Changed ranking profile"
        planner.updateProfile(edited)
        pending.resume(returning: (replyData(), HTTPURLResponse(url: URL(string: "http://127.0.0.1:8765/chat")!, statusCode: 200, httpVersion: nil, headerFields: nil)!))
        try await Task.sleep(for: .milliseconds(30))
        XCTAssertTrue(planner.messages.allSatisfy { $0.eventDraft == nil })
        XCTAssertTrue(planner.peopleToMeet.isEmpty)
        planner.reset()
    }
}
