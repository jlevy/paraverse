import XCTest
@testable import CommonGround

final class KnowledgeBaseBrowserTests: XCTestCase {
    func testRepositoryIsFoundFromAppAndExplicitOverrideIsAuthoritative() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        for path in ["db/src/paraverse_graph", "native"] {
            try FileManager.default.createDirectory(at: root.appendingPathComponent(path), withIntermediateDirectories: true)
        }
        try Data().write(to: root.appendingPathComponent("db/src/paraverse_graph/cli.py"))
        try Data().write(to: root.appendingPathComponent("native/Package.swift"))
        let app = root.appendingPathComponent("native/build/Paraverse.app")
        XCTAssertEqual(try KnowledgeBaseRuntime.repositoryRoot(environment: [:], bundleURL: app, sourceURL: nil).path, root.path)
        XCTAssertThrowsError(try KnowledgeBaseRuntime.repositoryRoot(environment: ["PARAVERSE_REPO_ROOT": "/missing/paraverse"], bundleURL: app, sourceURL: nil))
    }

    func testOnlyGraphBrowserMetadataIsRecognized() {
        let metadata = Data("""
        {"graph":"combined","dataset":"all","kb_digest":"abc","node_total":2,"edge_total":1,
         "groups":[{"title":"People","kinds":[{"kind":"person","title":"People","count":2}]}],
         "relationships":{"KNOWS":1}}
        """.utf8)
        XCTAssertTrue(KnowledgeBaseProbe.recognizesMetadata(metadata))
        for unrelated in ["<html>Other app</html>", "{\"status\":\"ok\"}", "{\"graph\":\"something\"}"] {
            XCTAssertFalse(KnowledgeBaseProbe.recognizesMetadata(Data(unrelated.utf8)))
        }
    }

    func testReuseRequiresIntendedDatasetSetAndContentDigest() throws {
        let metadata = Data(#"{"graph":"combined","dataset":"all","kb_digest":"expected","node_total":2,"edge_total":1,"groups":[],"relationships":{}}"#.utf8)
        let expected = KnowledgeBaseRuntime.ExpectedSelection(selected: ["one", "two"], kb_digest: "expected")
        func selection(_ names: [String]) throws -> Data {
            try JSONSerialization.data(withJSONObject: ["selection_enabled": true, "selected": names])
        }
        XCTAssertTrue(KnowledgeBaseProbe.matchesSelection(metadata: metadata, selection: try selection(["two", "one"]), expected: expected))
        for names in [["one"], ["other"], ["one", "two", "other"]] {
            XCTAssertFalse(KnowledgeBaseProbe.matchesSelection(metadata: metadata, selection: try selection(names), expected: expected))
        }
        let stale = KnowledgeBaseRuntime.ExpectedSelection(selected: ["one", "two"], kb_digest: "stale")
        XCTAssertFalse(KnowledgeBaseProbe.matchesSelection(metadata: metadata, selection: try selection(["one", "two"]), expected: stale))
    }

    @MainActor func testExistingServerIsReusedAndConflictingServiceIsLeftAlone() async {
        for response in [KnowledgeBaseProbe.ready, .unavailable("Another service owns this port")] {
            var launches = 0
            let server = KnowledgeBaseBrowserServer(probe: { response }, makeProcess: {
                launches += 1
                return Process()
            })
            await server.connect()
            XCTAssertEqual(launches, 0)
            XCTAssertEqual(server.state, response == .ready ? .ready : .failed("Another service owns this port"))
            server.stop()
            XCTAssertEqual(server.state, .stopped)
        }
    }

    @MainActor func testExplicitStopTerminatesOnlyOwnedChild() async throws {
        let external = sleeper()
        try external.run()
        defer { if external.isRunning { external.terminate() } }
        let child = sleeper()
        var probes = 0
        let server = KnowledgeBaseBrowserServer(probe: {
            probes += 1
            return probes == 1 ? .absent : .ready
        }, makeProcess: { child })
        await server.connect()
        XCTAssertEqual(server.state, .ready)
        XCTAssertTrue(child.isRunning)
        server.stop()
        for _ in 0..<100 where child.isRunning { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertFalse(child.isRunning)
        XCTAssertTrue(external.isRunning)
    }

    @MainActor func testClosingDuringStartupDoesNotPublishAStaleReadyState() async throws {
        let child = sleeper()
        let server = KnowledgeBaseBrowserServer(probe: { .absent }, makeProcess: { child })
        let connection = Task { await server.connect() }
        for _ in 0..<100 where !child.isRunning { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertTrue(child.isRunning)
        server.browserWindowClosed()
        await connection.value
        XCTAssertEqual(server.state, .stopped)
        for _ in 0..<100 where child.isRunning { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertFalse(child.isRunning)
    }

    @MainActor func testReadyServerStaysWarmAcrossBrowserWindowReopening() async throws {
        let child = sleeper()
        defer { if child.isRunning { kill(child.processIdentifier, SIGKILL) } }
        var launches = 0
        let server = KnowledgeBaseBrowserServer(probe: {
            child.isRunning ? .ready : .absent
        }, makeProcess: {
            launches += 1
            return child
        })
        await server.connect()
        XCTAssertEqual(server.state, .ready)
        let firstPage = server.pageID
        server.browserWindowClosed()
        XCTAssertTrue(child.isRunning)
        XCTAssertEqual(server.state, .ready)
        await server.connect()
        XCTAssertEqual(launches, 1)
        XCTAssertNotEqual(server.pageID, firstPage)
        XCTAssertEqual(server.state, .ready)
        server.stop()
        for _ in 0..<100 where child.isRunning { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertFalse(child.isRunning)
    }

    @MainActor func testLostWarmServerRestartsAsCancellableStartup() async throws {
        let first = sleeper()
        let replacement = sleeper()
        defer {
            for child in [first, replacement] where child.isRunning { kill(child.processIdentifier, SIGKILL) }
        }
        let status = ReopenProbeState()
        let server = KnowledgeBaseBrowserServer(probe: {
            status.reopening ? .absent : (first.isRunning ? .ready : .absent)
        }, makeProcess: {
            status.launches += 1
            return status.launches == 1 ? first : replacement
        })
        await server.connect()
        server.browserWindowClosed()
        status.reopening = true
        let connection = Task { await server.connect() }
        for _ in 0..<100 where !replacement.isRunning { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertTrue(replacement.isRunning)
        XCTAssertEqual(server.state, .starting)
        server.browserWindowClosed()
        await connection.value
        XCTAssertEqual(server.state, .stopped)
        for _ in 0..<100 where replacement.isRunning { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertFalse(first.isRunning)
        XCTAssertFalse(replacement.isRunning)
    }

    @MainActor func testImmediateReopenWaitsForTermResistantOwnedChild() async throws {
        let ready = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: ready) }
        let first = Process()
        first.executableURL = URL(fileURLWithPath: "/bin/sh")
        first.arguments = ["-c", "trap '' TERM; printf ready > \"$1\"; exec /bin/sleep 30", "kb-test", ready.path]
        let replacement = sleeper()
        defer {
            for child in [first, replacement] where child.isRunning { kill(child.processIdentifier, SIGKILL) }
        }
        let status = ReopenProbeState()
        let server = KnowledgeBaseBrowserServer(probe: {
            if first.isRunning {
                if status.reopening { status.probedDyingChild = true }
                return FileManager.default.fileExists(atPath: ready.path) ? .ready : .absent
            }
            return replacement.isRunning ? .ready : .absent
        }, makeProcess: {
            status.launches += 1
            return status.launches == 1 ? first : replacement
        }, shutdownGrace: .milliseconds(100))
        await server.connect()
        XCTAssertEqual(server.state, .ready)
        status.reopening = true
        server.stop()
        XCTAssertTrue(first.isRunning)
        await server.connect()
        XCTAssertFalse(status.probedDyingChild, "A child pending shutdown must never be reused as an external server")
        XCTAssertFalse(first.isRunning)
        XCTAssertEqual(status.launches, 2)
        XCTAssertTrue(replacement.isRunning)
        XCTAssertEqual(server.state, .ready)
        server.stop()
    }

    @MainActor private final class ReopenProbeState {
        var launches = 0
        var reopening = false
        var probedDyingChild = false
    }

    private func sleeper() -> Process {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/bin/sleep")
        process.arguments = ["30"]
        return process
    }
}
