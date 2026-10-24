import XCTest
@testable import CommonGround

final class ProfileTests: XCTestCase {
    private struct StubImporter: ProfileImporting {
        var result: ImportedProfile?
        func read(linkedIn: String?, x: String?, github: String?) async throws -> ImportedProfile {
            guard let result else { throw ProfileImportError.failed }
            return result
        }
    }

    func testFailedAndEmptyImportsPreserveReviewedProfile() async {
        var profile = AttendeeProfile()
        profile.background = "Builds developer tools."
        profile.interests = ["Open source"]
        let original = profile
        for importer in [StubImporter(), StubImporter(result: ImportedProfile(background: "", interests: []))] {
            do {
                profile = try await ProfileEnrichment.refresh(profile, using: importer)
                XCTFail("An unsuccessful import must report failure")
            } catch {}
            XCTAssertEqual(profile, original)
        }
    }

    func testPartialImportKeepsBioAndSelectedInterests() async throws {
        var profile = AttendeeProfile()
        profile.background = "Builds developer tools."
        profile.interests = ["Open source", "Photography"]
        let importer = StubImporter(result: ImportedProfile(background: "", interests: [InterestSuggestion(label: "AI", reason: "Discusses AI")]))
        let updated = try await ProfileEnrichment.refresh(profile, using: importer)
        XCTAssertEqual(updated.background, profile.background)
        XCTAssertEqual(updated.interests, ["Open source", "Photography", "AI"])
    }

    @MainActor func testDamagedDraftRecoversOnlyFromSameIdentity() throws {
        let defaults = UserDefaults(suiteName: "ProfileRecovery.\(UUID())")!
        defer { defaults.removeObject(forKey: "onboardingDraft"); defaults.removeObject(forKey: "previousWorkspace") }
        var saved = AttendeeProfile()
        saved.name = "Alex"; saved.background = "Developer"; saved.interests = ["Tools"]
        saved.linkedInURL = "https://linkedin.com/in/alex"
        saved.interestSuggestions = [InterestSuggestion(label: "Tools", reason: "Builds tools")]
        defaults.set(["attendeeProfile": try JSONEncoder().encode(saved)], forKey: "previousWorkspace")
        var damaged = saved; damaged.background = ""; damaged.interests = []
        defaults.set(try JSONEncoder().encode(damaged), forKey: "onboardingDraft")
        XCTAssertEqual(ProfileStore(defaults: defaults).profile.background, saved.background)
        XCTAssertEqual(ProfileStore(defaults: defaults).profile.interests, saved.interests)
        damaged.linkedInURL = "https://linkedin.com/in/someone-else"
        defaults.set(try JSONEncoder().encode(damaged), forKey: "onboardingDraft")
        XCTAssertTrue(ProfileStore(defaults: defaults).profile.background.isEmpty)
    }

    func testOnboardingRequiresBothProfileLinks() {
        var profile = AttendeeProfile()
        XCTAssertFalse(profile.hasRequiredSocialProfiles)
        profile.linkedInURL = "https://www.linkedin.com/in/jlevy/"
        XCTAssertFalse(profile.hasRequiredSocialProfiles)
        profile.xURL = "https://x.com/home"
        XCTAssertFalse(profile.hasRequiredSocialProfiles)
        profile.xURL = "https://x.com/ojoshe"
        XCTAssertTrue(profile.hasRequiredSocialProfiles)
        profile.linkedInURL = "https://example.com/in/jlevy"
        XCTAssertFalse(profile.hasRequiredSocialProfiles)
    }

    @MainActor func testProfilePersistsAndSkipsOnboarding() {
        let suite = "CommonGroundTests.\(UUID())"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let store = ProfileStore(defaults: defaults)
        XCTAssertEqual(store.stage, 0)
        var profile = AttendeeProfile()
        profile.name = "Alex Test"
        profile.city = "Oakland"
        profile.interests = ["Open source", "Live music"]
        profile.personalInterests = ["Live music"]
        profile.interestSuggestions = [InterestSuggestion(label: "Live music", reason: "Discusses concerts", category: "personal", evidence: [ProfileEvidence(sourceURL: URL(string: "https://example.com/post")!, quote: "I enjoy concerts")])]
        profile.conferences = ["GitHub Universe"]
        store.save(profile)
        let restored = ProfileStore(defaults: defaults)
        XCTAssertEqual(restored.stage, 4)
        XCTAssertEqual(restored.profile, profile)
        XCTAssertEqual(restored.profile.initials, "AT")
    }
    @MainActor func testSwitchProfilePreservesWorkspaceAndCalendar() {
        let suite = "CommonGroundTests.\(UUID())"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let store = ProfileStore(defaults: defaults)
        var sam = AttendeeProfile(); sam.name = "Sam"; sam.city = "SF"; sam.interests = ["Databases"]
        store.save(sam)
        defaults.set(Data([1,2,3]), forKey: "lastSessionPlan")
        defaults.set("connected-calendar", forKey: "calendarID")
        store.startNewProfile()
        XCTAssertTrue(store.profile.name.isEmpty)
        XCTAssertNil(defaults.data(forKey: "lastSessionPlan"))
        XCTAssertEqual(defaults.string(forKey: "calendarID"), "connected-calendar")
        store.restorePrevious()
        XCTAssertEqual(store.profile, sam)
        XCTAssertEqual(defaults.data(forKey: "lastSessionPlan"), Data([1,2,3]))
    }
    @MainActor func testDraftSurvivesRestartAndLogoutButNewProfileClearsIt() {
        let suite = "CommonGroundTests.\(UUID())"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let store = ProfileStore(defaults: defaults)
        var draft = AttendeeProfile()
        draft.name = "Joshua Levy"
        draft.city = "San Francisco"
        draft.linkedInURL = "https://www.linkedin.com/in/jlevy/"
        draft.xURL = "https://x.com/ojoshe"
        store.saveDraft(draft)
        XCTAssertEqual(ProfileStore(defaults: defaults).profile, draft)
        XCTAssertEqual(ProfileStore(defaults: defaults).stage, 0)
        store.logOut()
        XCTAssertEqual(store.profile, draft)
        store.startNewProfile()
        XCTAssertTrue(ProfileStore(defaults: defaults).profile.name.isEmpty)
    }
    func testBlankProfileCannotContinue() {
        var profile = AttendeeProfile()
        profile.name = "  "
        profile.city = "San Francisco"
        profile.interests = ["Design tools"]
        XCTAssertFalse(profile.isValid)
    }
    func testCustomInterestsTrimAndDeduplicate() {
        var selected: Set<String> = ["Design tools"]
        InterestSelection.add(" design TOOLS ", to: &selected)
        InterestSelection.add("  Open source  ", to: &selected)
        InterestSelection.add("  ", to: &selected)
        XCTAssertEqual(selected, ["Design tools", "Open source"])
    }
    func testSavingDoesNotAutomaticallyOptIntoMatching() throws {
        var profile = AttendeeProfile()
        let event = ConferenceRecord(id: "test", title: "Test Conference", start: "2026-11-01", end: "2026-11-02", dates: "November 1–2", city: "Test City", venue: "Test Venue", price: "Unknown", url: "https://example.com", online: false, themes: [], program: "Test")
        profile.setStatus(.going, for: event)
        XCTAssertNil(profile.groupMatchingIDs)
        profile.groupMatchingIDs = [event.id]
        let restored = try JSONDecoder().decode(AttendeeProfile.self, from: JSONEncoder().encode(profile))
        XCTAssertEqual(restored.status(for: event.id), .going)
        XCTAssertEqual(restored.groupMatchingIDs, [event.id])
        profile.setStatus(.none, for: event)
        XCTAssertTrue(profile.groupMatchingIDs!.isEmpty)
    }
    func testUnconfiguredImportDoesNotInventInterests() async {
        do {
            _ = try await ProfileImportClient(endpoint: nil).read(linkedIn: "https://linkedin.com/in/test", x: nil)
            XCTFail("Should report unavailable")
        } catch { XCTAssertTrue(error is ProfileImportError) }
    }
}
