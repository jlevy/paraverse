import SwiftUI

/// Bespoke artwork is shown only for the profile it was created for.
struct ProfileCharacter: View {
    let profile: AttendeeProfile
    var size: CGFloat = 96
    private static let joshua = NSImage(contentsOf: worldAsset("WorldArt/joshua-levy-portrait-teal.png"))

    private var isJoshua: Bool {
        let name = profile.name.split(whereSeparator: \.isWhitespace).joined(separator: " ").lowercased()
        return name == "joshua levy" || name == "josh levy"
    }

    var body: some View {
        if isJoshua, let image = Self.joshua {
            Image(nsImage: image)
                .resizable()
                .interpolation(.none)
                .scaledToFit()
                .frame(width: size, height: size)
                .padding(8)
                .background(PixelPanel().fill(Brand.buttonSecondary))
                .clipShape(PixelPanel())
                .overlay(PixelPanel().stroke(Brand.buttonBorder, lineWidth: 2))
                .accessibilityLabel("Pixel-art portrait of Joshua Levy")
        }
    }
}
