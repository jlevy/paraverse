import AppKit

extension WorldCharacter {
    // Slice the generated sprite atlases once, rather than decoding them while scrolling.
    @MainActor private static let portraits: [String: NSImage] = {
        var result: [String: NSImage] = [:]
        var sheets: [String: NSBitmapImageRep] = [:]
        for character in all {
            if let cell = character.atlasCell {
                if sheets[character.sprite] == nil,
                   let data = try? Data(contentsOf: worldAsset("WorldArt/" + character.sprite)) {
                    sheets[character.sprite] = NSBitmapImageRep(data: data)
                }
                guard let sheet = sheets[character.sprite]?.cgImage else { continue }
                guard cell >= 0, cell < 4 else { continue }
                let width = sheet.width / 2, height = sheet.height / 2
                let rect = CGRect(x: (cell % 2) * width, y: (cell / 2) * height, width: width, height: height)
                guard let cellImage = sheet.cropping(to: rect) else { continue }
                result[character.personID] = NSImage(cgImage: cellImage, size: NSSize(width: width, height: height))
            } else if let image = NSImage(contentsOf: worldAsset("WorldArt/" + character.sprite)) {
                result[character.personID] = image
            }
        }
        return result
    }()

    @MainActor private static var alignedPortraits: [String: NSImage] = [:]
    @MainActor static func directoryImage(for personID: String) -> NSImage? {
        if let cached = alignedPortraits[personID] { return cached }
        guard let image = recommendationImage(for: personID),
              let source = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return nil }
        let w = source.width, h = source.height
        guard let context = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8,
            bytesPerRow: w * 4, space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue), let data = context.data else { return image }
        context.draw(source, in: CGRect(x: 0, y: 0, width: w, height: h))
        let bytes = data.assumingMemoryBound(to: UInt8.self)
        var left = w, right = 0, top = h, bottom = 0
        for y in 0..<h { for x in 0..<w where bytes[(y * w + x) * 4 + 3] > 128 {
            left = min(left, x); right = max(right, x); top = min(top, y); bottom = max(bottom, y)
        } }
        guard left <= right, top <= bottom,
              let cropped = context.makeImage()?.cropping(to: CGRect(x: left, y: top, width: right-left+1, height: bottom-top+1)) else { return image }
        let result = NSImage(cgImage: cropped, size: NSSize(width: cropped.width, height: cropped.height))
        alignedPortraits[personID] = result
        return result
    }

    @MainActor static func image(for personID: String) -> NSImage? {
        portraits[personID] ?? NSImage(contentsOf: worldAsset("WorldArt/player.png"))
    }

    @MainActor static func recommendationImage(for personID: String) -> NSImage? {
        let id = personID.lowercased()
        guard let character = all.first(where: {
            $0.personID.lowercased() == id || $0.personID.lowercased() == "attendee:" + id
        }) else { return nil }
        return portraits[character.personID]
    }
}
