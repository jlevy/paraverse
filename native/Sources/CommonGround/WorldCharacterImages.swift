import AppKit

extension WorldCharacter {
    // Slice the generated 2×2 atlases once, rather than decoding them while scrolling.
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
