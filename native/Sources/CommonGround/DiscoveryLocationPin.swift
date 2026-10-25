import SwiftUI

/// A small grid-drawn pin keeps location metadata consistent with the pixel artwork.
struct DiscoveryLocationPin: View {
    private let pixels = [
        "...rrr...",
        "..rrrrr..",
        ".rrhhhrr.",
        "rrh...rrr",
        "rrh...rrr",
        "rrr...rrr",
        ".rrrrrrr.",
        ".rrrrrrr.",
        "..rrrrr..",
        "...rrr...",
        "...rrr...",
        "....r...."
    ]

    var body: some View {
        Canvas { context, size in
            let unit = min(size.width / 9, size.height / 12)
            for (y, row) in pixels.enumerated() {
                for (x, pixel) in row.enumerated() where pixel != "." {
                    let color = pixel == "h"
                        ? Color(red: 1, green: 0.56, blue: 0.48)
                        : Color(red: 0.93, green: 0.29, blue: 0.29)
                    let rect = CGRect(x: CGFloat(x) * unit, y: CGFloat(y) * unit, width: unit, height: unit)
                    context.fill(Path(rect), with: .color(color))
                }
            }
        }
    }
}
