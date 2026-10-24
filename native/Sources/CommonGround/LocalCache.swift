import SwiftUI
import CryptoKit
import ImageIO

enum LocalCache {
    static func key(_ value: String) -> String { SHA256.hash(data: Data(value.utf8)).map { String(format: "%02x", $0) }.joined() }
    static let directory: URL = {
        let url = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0].appendingPathComponent("CommonGround", isDirectory: true)
        try? FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        return url
    }()
}

@MainActor final class ImageCache {
    static let shared = ImageCache()
    private let memory = NSCache<NSString, NSImage>()
    private var pending: [URL: Task<NSImage?, Never>] = [:]
    private var failures: [URL: Date] = [:]
    init() { memory.totalCostLimit = 64 * 1024 * 1024 }
    private func decode(_ data: Data) -> NSImage? {
        guard let source = CGImageSourceCreateWithData(data as CFData, nil),
              let image = CGImageSourceCreateThumbnailAtIndex(source, 0, [kCGImageSourceCreateThumbnailFromImageAlways: true, kCGImageSourceThumbnailMaxPixelSize: 1000, kCGImageSourceCreateThumbnailWithTransform: true] as CFDictionary) else { return nil }
        return NSImage(cgImage: image, size: .zero)
    }
    func cached(_ url: URL) -> NSImage? {
        let key = LocalCache.key(url.absoluteString)
        if let image = memory.object(forKey: key as NSString) { return image }
        let bundled = Bundle.main.resourceURL?.appendingPathComponent("CachedImages/\(key).image")
        let disk = LocalCache.directory.appendingPathComponent("\(key).image")
        for location in [bundled, disk].compactMap({ $0 }) {
            if let data = try? Data(contentsOf: location), let image = decode(data) {
                memory.setObject(image, forKey: key as NSString, cost: Int(image.size.width * image.size.height * 4))
                return image
            }
        }
        return nil
    }
    func load(_ url: URL) async -> NSImage? {
        if let image = cached(url) { return image }
        if let task = pending[url] { return await task.value }
        guard url.scheme == "https", failures[url].map({ Date().timeIntervalSince($0) > 60 }) ?? true else { return nil }
        let task = Task<NSImage?, Never> {
            do {
                var request = URLRequest(url: url); request.timeoutInterval = 8
                let (data, response) = try await URLSession.shared.data(for: request)
                guard let response = response as? HTTPURLResponse, response.statusCode == 200,
                      data.count <= 8_000_000, let image = decode(data) else { return nil }
                let key = LocalCache.key(url.absoluteString)
                try? data.write(to: LocalCache.directory.appendingPathComponent("\(key).image"), options: .atomic)
                memory.setObject(image, forKey: key as NSString, cost: Int(image.size.width * image.size.height * 4))
                return image
            } catch { return nil }
        }
        pending[url] = task
        let image = await task.value
        pending[url] = nil
        if image == nil { failures[url] = Date() }
        return image
    }
    func preload(_ urls: [URL]) async {
        // Small batches keep cold starts from flooding the network.
        let unique = Array(Set(urls))
        for start in stride(from: 0, to: unique.count, by: 4) {
            await withTaskGroup(of: Void.self) { group in
                for url in unique[start..<min(start + 4, unique.count)] { group.addTask { _ = await self.load(url) } }
            }
        }
    }
}

struct CachedRemoteImage<Placeholder: View>: View {
    let url: URL
    @ViewBuilder var placeholder: () -> Placeholder
    @State private var image: NSImage?
    init(url: URL, @ViewBuilder placeholder: @escaping () -> Placeholder) {
        self.url = url; self.placeholder = placeholder
        _image = State(initialValue: ImageCache.shared.cached(url))
    }
    var body: some View {
        Group {
            if let image { Image(nsImage: image).resizable().scaledToFill() }
            else { placeholder() }
        }.task(id: url) { image = ImageCache.shared.cached(url); image = await ImageCache.shared.load(url) }
    }
}
