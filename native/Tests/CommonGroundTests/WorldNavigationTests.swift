import AppKit
import SwiftUI
import XCTest
@testable import CommonGround

final class WorldNavigationTests: XCTestCase {
    @MainActor func testExploreMenuExposesAndDispatchesEveryWorkspaceRoute() {
        var selected = "world"
        let menu = WorldNavigationMenu(openDiscovery: { selected = "discover" }, openSchedule: { selected = "schedule" }, openPeople: { selected = "people" })
        XCTAssertEqual(menu.destinations.map(\.title), ["All conferences", "My schedule", "People directory"])
        for destination in menu.destinations {
            destination.open()
            XCTAssertEqual(selected, destination.id)
        }
        let host = NSHostingView(rootView: menu)
        XCTAssertGreaterThan(host.fittingSize.width, 44)
        XCTAssertGreaterThanOrEqual(host.fittingSize.height, 44)
    }
}
