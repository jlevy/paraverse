// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "CommonGround", platforms: [.macOS(.v14)], products: [.executable(name: "CommonGround", targets: ["CommonGround"])], targets: [.executableTarget(name: "CommonGround"), .testTarget(name: "CommonGroundTests", dependencies: ["CommonGround"])])
