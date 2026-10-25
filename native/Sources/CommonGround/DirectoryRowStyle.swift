import SwiftUI

struct DirectoryRowStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        Row(configuration: configuration)
    }

    private struct Row: View {
        let configuration: ButtonStyleConfiguration
        @State private var hovered = false

        var body: some View {
            configuration.label
                .contentShape(PixelPanel())
                .background(PixelPanel().fill(Color.teal.opacity(configuration.isPressed ? 0.22 : hovered ? 0.16 : 0.06)))
                .onHover { hovered = $0 }
        }
    }
}

struct PixelSearchIcon: Shape {
    func path(in rect: CGRect) -> Path {
        let pixels = ["001111000000", "011001100000", "110000110000", "100000010000", "100000010000", "110000110000", "011001100000", "001111110000", "000000011000", "000000001100", "000000000110", "000000000011"]
        var path = Path()
        let unit = min(rect.width, rect.height) / 12
        for (y, row) in pixels.enumerated() {
            for (x, pixel) in row.enumerated() where pixel == "1" {
                path.addRect(CGRect(x: rect.minX + CGFloat(x) * unit, y: rect.minY + CGFloat(y) * unit, width: unit, height: unit))
            }
        }
        return path
    }
}
