import XCTest
@testable import CommonGround

final class CacheTests: XCTestCase {
    @MainActor func testRecommendationsSurviveMemoryResetAndRespectProfileChanges() throws {
        var profile = AttendeeProfile(); profile.city = "cache-test-" + UUID().uuidString; profile.interests = ["Design"]
        let query = ConferenceQuery(profile)
        let result = ConferenceResults(matches: [.featuredUniverse], generatedAt: "2026-10-23", searchedCount: 1, verifiedCount: 1, summary: "Test")
        let key = LocalCache.key("six-recommendations-v2:" + query.identity)
        let file = LocalCache.directory.appendingPathComponent(key + ".json")
        defer { try? FileManager.default.removeItem(at: file); ConferenceMemory.results.removeValue(forKey: key) }
        ConferenceMemory.save(result, for: query)
        ConferenceMemory.results.removeValue(forKey: key)
        XCTAssertEqual(ConferenceMemory.cached(query)?.matches.first?.id, "universe-2026")
        profile.travel = "Online"
        XCTAssertNil(ConferenceMemory.cached(ConferenceQuery(profile)))
        profile.travel = "Nearby"; profile.interests = ["Databases"]
        XCTAssertNil(ConferenceMemory.cached(ConferenceQuery(profile)))
        ConferenceMemory.results[key] = .init(savedAt: Date().addingTimeInterval(-21601), result: result)
        XCTAssertNil(ConferenceMemory.cached(query))
    }
}
