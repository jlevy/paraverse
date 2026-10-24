import AppKit
import Foundation
import Observation
import SwiftUI
import WebKit

enum KnowledgeBaseRuntime {
    static let rootEnvironmentKey = "PARAVERSE_REPO_ROOT"

    enum SetupError: LocalizedError {
        case repositoryMissing, invalidOverride(String), pythonMissing(String)
        var errorDescription: String? {
            switch self {
            case .repositoryMissing:
                return "The knowledge base repository could not be found. Keep the app in native/build, or set PARAVERSE_REPO_ROOT to the repository folder."
            case .invalidOverride(let path):
                return "PARAVERSE_REPO_ROOT does not contain a Paraverse repository: \(path)"
            case .pythonMissing(let path):
                return "The graph browser runtime is missing at \(path). Run make install in the repository’s db folder, then try again."
            }
        }
    }

    static func repositoryRoot(
        environment: [String: String] = ProcessInfo.processInfo.environment,
        bundleURL: URL = Bundle.main.bundleURL,
        sourceURL: URL? = URL(fileURLWithPath: #filePath)
    ) throws -> URL {
        func isRepository(_ url: URL) -> Bool {
            ["db/src/paraverse_graph/cli.py", "native/Package.swift"].allSatisfy {
                FileManager.default.fileExists(atPath: url.appendingPathComponent($0).path)
            }
        }
        if let explicit = environment[rootEnvironmentKey], !explicit.isEmpty {
            let root = URL(fileURLWithPath: explicit).standardizedFileURL
            guard isRepository(root) else { throw SetupError.invalidOverride(explicit) }
            return root
        }
        // Source-location discovery is a local development fallback. Installed apps
        // resolve from their bundle location or the explicit environment override.
        var candidates = [bundleURL]
        if let sourceURL, FileManager.default.fileExists(atPath: sourceURL.path) {
            candidates.append(sourceURL.deletingLastPathComponent())
        }
        for candidate in candidates {
            var ancestor = candidate.standardizedFileURL
            while ancestor.path != "/" {
                if isRepository(ancestor) { return ancestor }
                ancestor.deleteLastPathComponent()
            }
        }
        throw SetupError.repositoryMissing
    }

    struct ExpectedSelection: Codable, Sendable {
        let selected: [String]
        let kb_digest: String
    }

    static func expectedSelection() async throws -> ExpectedSelection {
        try await Task.detached {
            let process = try command("describe")
            let output = Pipe(); let errors = Pipe()
            process.standardOutput = output
            process.standardError = errors
            try process.run()
            let data = output.fileHandleForReading.readDataToEndOfFile()
            process.waitUntilExit()
            guard process.terminationStatus == 0 else {
                throw NSError(domain: "KnowledgeBaseRuntime", code: Int(process.terminationStatus), userInfo: [NSLocalizedDescriptionKey: "The intended local datasets could not be read. Check that their knowledge bases are built."])
            }
            return try JSONDecoder().decode(ExpectedSelection.self, from: data)
        }.value
    }

    static func makeProcess() throws -> Process { try command("serve") }

    private static func command(_ operation: String) throws -> Process {
        let root = try repositoryRoot()
        let python = root.appendingPathComponent("db/.venv/bin/python")
        guard FileManager.default.isExecutableFile(atPath: python.path) else {
            throw SetupError.pythonMissing(python.path)
        }
        let process = Process()
        process.executableURL = python
        process.currentDirectoryURL = root.appendingPathComponent("db")
        process.arguments = [root.appendingPathComponent("backend/kb_browser_runtime.py").path, operation]
        var environment = ProcessInfo.processInfo.environment
        environment["PYTHONPATH"] = root.appendingPathComponent("db/src").path
        environment["PYTHONUNBUFFERED"] = "1"
        process.environment = environment
        return process
    }
}

enum KnowledgeBaseProbe: Equatable {
    case ready, absent, unavailable(String)

    static func recognizesMetadata(_ data: Data) -> Bool {
        struct Metadata: Decodable {
            struct Group: Decodable {
                struct Kind: Decodable { let kind: String; let title: String; let count: Int }
                let title: String
                let kinds: [Kind]
            }
            let graph: String
            let dataset: String
            let kb_digest: String
            let node_total: Int
            let edge_total: Int
            let groups: [Group]
            let relationships: [String: Int]
        }
        guard let meta = try? JSONDecoder().decode(Metadata.self, from: data) else { return false }
        return !meta.graph.isEmpty && !meta.dataset.isEmpty && !meta.kb_digest.isEmpty
            && meta.node_total >= 0 && meta.edge_total >= 0
    }

    static func matchesSelection(metadata: Data, selection: Data, expected: KnowledgeBaseRuntime.ExpectedSelection) -> Bool {
        struct Selection: Decodable {
            let selection_enabled: Bool
            let selected: [String]
        }
        guard recognizesMetadata(metadata),
              let meta = try? JSONSerialization.jsonObject(with: metadata) as? [String: Any],
              let actual = try? JSONDecoder().decode(Selection.self, from: selection),
              actual.selection_enabled, !expected.selected.isEmpty else { return false }
        return actual.selected.sorted() == expected.selected.sorted()
            && meta["kb_digest"] as? String == expected.kb_digest
    }

}

private final class BrowserProbeDelegate: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}

@MainActor @Observable final class KnowledgeBaseBrowserServer {
    static let shared = KnowledgeBaseBrowserServer()
    static let address = URL(string: "http://127.0.0.1:8766/")!

    enum State: Equatable { case stopped, starting, ready, failed(String) }
    private(set) var state: State = .stopped
    private(set) var pageID = UUID()
    private var ownedProcess: Process?
    private struct PendingShutdown {
        let id: UUID
        let task: Task<Void, Never>
    }
    private var pendingShutdown: PendingShutdown?
    private var activeAttempt: UUID?
    private var outputURL: URL?
    private var outputHandle: FileHandle?
    private let probe: @MainActor () async -> KnowledgeBaseProbe
    private let makeProcess: @MainActor () throws -> Process
    private let startupTimeout: Duration
    private let shutdownGrace: Duration

    init(
        probe: @escaping @MainActor () async -> KnowledgeBaseProbe = KnowledgeBaseBrowserServer.probeServer,
        makeProcess: @escaping @MainActor () throws -> Process = KnowledgeBaseRuntime.makeProcess,
        startupTimeout: Duration = .seconds(120),
        shutdownGrace: Duration = .seconds(35)
    ) {
        self.probe = probe
        self.makeProcess = makeProcess
        self.startupTimeout = startupTimeout
        self.shutdownGrace = shutdownGrace
    }

    static func probeServer() async -> KnowledgeBaseProbe {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.connectionProxyDictionary = [:]
        let session = URLSession(configuration: configuration, delegate: BrowserProbeDelegate(), delegateQueue: nil)
        defer { session.invalidateAndCancel() }
        let request = URLRequest(url: address.appendingPathComponent("api/meta"), cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 3)
        do {
            let (data, response) = try await session.data(for: request)
            guard let response = response as? HTTPURLResponse, response.statusCode == 200,
                  KnowledgeBaseProbe.recognizesMetadata(data) else {
                return .unavailable("Port 8766 is responding, but it is not a ready Paraverse knowledge base browser. Stop the other service or start the graph browser, then try again.")
            }
            let expected = try await KnowledgeBaseRuntime.expectedSelection()
            let selectionRequest = URLRequest(url: address.appendingPathComponent("api/datasets"), cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 3)
            let (selection, selectionResponse) = try await session.data(for: selectionRequest)
            guard (selectionResponse as? HTTPURLResponse)?.statusCode == 200,
                  KnowledgeBaseProbe.matchesSelection(metadata: data, selection: selection, expected: expected) else {
                return .unavailable("Port 8766 serves different datasets or different knowledge base content than this app’s local repository. That service has been left running. Stop it yourself or use the intended repository, then try again.")
            }
            return .ready
        } catch let error as URLError where error.code == .cannotConnectToHost {
            return .absent
        } catch {
            return .unavailable("The local knowledge base browser could not be reached: \(error.localizedDescription)")
        }
    }

    func connect() async {
        let attempt = UUID()
        activeAttempt = attempt
        if state != .ready { state = .starting }
        await waitForOwnedShutdown()
        guard isCurrent(attempt) else { return }
        let initial = await probe()
        guard isCurrent(attempt) else { return }
        switch initial {
        case .ready:
            showBrowser()
            return
        case .unavailable(let message):
            fail(message)
            return
        case .absent:
            state = .starting
            break
        }
        do {
            releaseOwnedProcess()
            await waitForOwnedShutdown()
            guard isCurrent(attempt) else { return }
            let process = try makeProcess()
            let log = FileManager.default.temporaryDirectory.appendingPathComponent("paraverse-kb-\(UUID().uuidString).log")
            guard FileManager.default.createFile(atPath: log.path, contents: nil, attributes: [.posixPermissions: 0o600]) else {
                throw CocoaError(.fileWriteUnknown)
            }
            outputURL = log
            let handle = try FileHandle(forWritingTo: log)
            outputHandle = handle
            process.standardOutput = handle
            process.standardError = handle
            process.terminationHandler = { [weak self] child in
                let pid = child.processIdentifier
                let status = child.terminationStatus
                Task { @MainActor in self?.processExited(pid: pid, status: status) }
            }
            try process.run()
            ownedProcess = process
        } catch {
            fail(error.localizedDescription)
            return
        }

        let deadline = ContinuousClock.now.advanced(by: startupTimeout)
        while isCurrent(attempt), ContinuousClock.now < deadline {
            let result = await probe()
            guard isCurrent(attempt) else { return }
            switch result {
            case .ready:
                showBrowser()
                return
            case .unavailable(let message):
                fail(message)
                return
            case .absent:
                break
            }
            do { try await Task.sleep(for: .milliseconds(250)) }
            catch { if activeAttempt == attempt { browserWindowClosed() }; return }
        }
        if isCurrent(attempt) {
            fail("The knowledge base browser did not become ready within two minutes. Try again after checking the graph runtime and datasets.")
        }
    }

    func stop() {
        activeAttempt = nil
        releaseOwnedProcess()
        state = .stopped
    }

    func browserWindowClosed() {
        activeAttempt = nil
        // Keep a ready browser warm for the next window; unfinished startup is
        // canceled so closing the window does not leave expensive work running.
        if state != .ready { stop() }
    }

    private func isCurrent(_ attempt: UUID) -> Bool {
        guard activeAttempt == attempt else { return false }
        if Task.isCancelled { browserWindowClosed(); return false }
        return true
    }

    private func showBrowser() {
        pageID = UUID()
        state = .ready
    }

    private func processExited(pid: Int32, status: Int32) {
        guard ownedProcess?.processIdentifier == pid else { return }
        fail("The knowledge base browser stopped (exit \(status)). Check that make install has completed in db and the dataset knowledge bases are built, then try again.")
    }

    private func fail(_ message: String) {
        activeAttempt = nil
        let detail = outputURL.flatMap { try? String(contentsOf: $0, encoding: .utf8) }?.trimmingCharacters(in: .whitespacesAndNewlines)
        releaseOwnedProcess()
        state = .failed(message + ((detail?.isEmpty == false) ? "\n\n" + String(detail!.suffix(1600)) : ""))
    }

    private func releaseOwnedProcess() {
        let process = ownedProcess
        ownedProcess = nil
        let log = outputURL
        let handle = outputHandle
        outputURL = nil
        outputHandle = nil
        process?.terminationHandler = nil
        try? handle?.close()
        if let log { try? FileManager.default.removeItem(at: log) }
        guard let process, process.isRunning else { return }
        process.terminate()
        let previousShutdown = pendingShutdown?.task
        let task = Task { @MainActor in
            await previousShutdown?.value
            // SIGTERM lets uvicorn and the embedded database clean up normally.
            // Escalate only for the exact child launched by this app.
            // redislite daemonizes and its atexit cleanup can exceed two seconds.
            // Give the native launcher time to reap its Redis daemon before any
            // exact-child fallback. Never signal an externally reused service.
            let deadline = ContinuousClock.now.advanced(by: shutdownGrace)
            while process.isRunning, ContinuousClock.now < deadline {
                try? await Task.sleep(for: .milliseconds(10))
            }
            if process.isRunning { kill(process.processIdentifier, SIGKILL) }
            while process.isRunning {
                try? await Task.sleep(for: .milliseconds(10))
            }
        }
        pendingShutdown = PendingShutdown(id: UUID(), task: task)
    }

    private func waitForOwnedShutdown() async {
        // A closing child can still answer requests until it exits. Keep it owned
        // until then so reopening never mistakes it for an external server.
        while let pending = pendingShutdown {
            await pending.task.value
            if pendingShutdown?.id == pending.id { pendingShutdown = nil }
        }
    }
}

struct KnowledgeBaseBrowser: View {
    @State private var server = KnowledgeBaseBrowserServer.shared
    @State private var retryID = UUID()
    @State private var pageLoading = true
    @State private var pageError: String?

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Knowledge Base").font(.headline)
                    Text("Browse the raw conference records").font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
                Button { retry() } label: { Label("Reload", systemImage: "arrow.clockwise") }
                    .disabled(server.state == .starting)
                    .help("Reconnect and reload the knowledge base")
            }.padding(16)
            Divider()
            Group {
                switch server.state {
                case .stopped, .starting:
                    ProgressView("Starting the knowledge base browser…").frame(maxWidth: .infinity, maxHeight: .infinity)
                case .failed(let message):
                    failure(message)
                case .ready:
                    ZStack {
                        KnowledgeBaseWebView(url: KnowledgeBaseBrowserServer.address, loading: $pageLoading, error: $pageError)
                            .id(server.pageID)
                        if let pageError { failure(pageError).background(.background) }
                        else if pageLoading { ProgressView("Loading records…").padding(20).background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12)) }
                    }
                }
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(minWidth: 900, minHeight: 620)
        .task(id: retryID) { await server.connect() }
        .onDisappear { server.browserWindowClosed() }
    }

    private func retry() {
        pageError = nil
        pageLoading = true
        retryID = UUID()
    }

    private func failure(_ message: String) -> some View {
        ScrollView {
            VStack(spacing: 16) {
                Image(systemName: "externaldrive.badge.exclamationmark").font(.system(size: 36)).foregroundStyle(.secondary)
                Text("Knowledge Base Unavailable").font(.title2.bold())
                Text(message).font(.callout).foregroundStyle(.secondary).textSelection(.enabled)
                Button("Try Again") { retry() }.buttonStyle(.borderedProminent)
            }.frame(maxWidth: 620).padding(40).frame(maxWidth: .infinity)
        }
    }
}

private struct KnowledgeBaseWebView: NSViewRepresentable {
    let url: URL
    @Binding var loading: Bool
    @Binding var error: String?

    func makeCoordinator() -> Coordinator { Coordinator(self) }
    func makeNSView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let view = WKWebView(frame: .zero, configuration: configuration)
        view.navigationDelegate = context.coordinator
        view.load(URLRequest(url: url))
        return view
    }
    func updateNSView(_ nsView: WKWebView, context: Context) { context.coordinator.parent = self }

    @MainActor final class Coordinator: NSObject, WKNavigationDelegate {
        var parent: KnowledgeBaseWebView
        init(_ parent: KnowledgeBaseWebView) { self.parent = parent }

        func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
            parent.loading = true
            parent.error = nil
        }
        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) { parent.loading = false }
        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { failed(error) }
        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { failed(error) }
        func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
            parent.loading = false
            parent.error = "The browser view stopped. Try again to reload the knowledge base."
        }
        private func failed(_ error: Error) {
            guard (error as NSError).code != NSURLErrorCancelled else { return }
            parent.loading = false
            parent.error = "The knowledge base page could not be loaded: \(error.localizedDescription)"
        }
        func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction) async -> WKNavigationActionPolicy {
            guard let target = navigationAction.request.url else { return .cancel }
            let origin = KnowledgeBaseBrowserServer.address
            if target.scheme == origin.scheme, target.host == origin.host, target.port == origin.port {
                if navigationAction.targetFrame == nil { webView.load(navigationAction.request); return .cancel }
                return .allow
            } else {
                if navigationAction.navigationType == .linkActivated, let scheme = target.scheme, ["http", "https"].contains(scheme) {
                    NSWorkspace.shared.open(target)
                }
                return .cancel
            }
        }
    }
}
