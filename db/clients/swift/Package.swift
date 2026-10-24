// swift-tools-version: 6.0
// A standalone Swift client for the paraverse-graph API. Its tests decode captured API
// responses, so they check that the JSON contract decodes in Swift.
import PackageDescription

let package = Package(
    name: "ParaverseGraphClient",
    platforms: [.macOS(.v14)],
    products: [.library(name: "ParaverseGraphClient", targets: ["ParaverseGraphClient"])],
    targets: [
        .target(name: "ParaverseGraphClient"),
        .testTarget(
            name: "ParaverseGraphClientTests",
            dependencies: ["ParaverseGraphClient"],
            resources: [.copy("Fixtures")]
        ),
    ]
)
