import XCTest
import SpriteKit
@testable import CommonGround

final class WorldCameraTests: XCTestCase {
    @MainActor func testZoomAndPanNeverExposeOutsideVenue() async {
        for viewport in [CGSize(width: 1180, height: 750), CGSize(width: 1800, height: 620), CGSize(width: 900, height: 1100)] {
            let scene = ConferenceScene(size: viewport)
            scene.zoomTo(100)
            XCTAssertLessThanOrEqual(viewport.width * scene.cameraNode.xScale, scene.extent.width + 0.001)
            XCTAssertLessThanOrEqual(viewport.height * scene.cameraNode.yScale, scene.extent.height + 0.001)
            for position in [CGPoint(x: -5000, y: -5000), CGPoint(x: 5000, y: 5000)] {
                scene.cameraNode.position = position
                scene.clampCamera()
                let halfWidth = viewport.width * scene.cameraNode.xScale / 2
                let halfHeight = viewport.height * scene.cameraNode.yScale / 2
                XCTAssertGreaterThanOrEqual(scene.cameraNode.position.x - halfWidth, -0.001)
                XCTAssertGreaterThanOrEqual(scene.cameraNode.position.y - halfHeight, -0.001)
                XCTAssertLessThanOrEqual(scene.cameraNode.position.x + halfWidth, scene.extent.width + 0.001)
                XCTAssertLessThanOrEqual(scene.cameraNode.position.y + halfHeight, scene.extent.height + 0.001)
            }
            scene.zoomTo(0.5)
            XCTAssertEqual(scene.cameraNode.xScale, 0.5, accuracy: 0.001)
        }
    }
}
