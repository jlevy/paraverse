import SwiftUI
import AppKit

// Semantic brand roles; each resolves for light, dark and increased contrast.
enum Brand {
    // Fixed artwork palette for the dark blue conference welcome screen.
    static let welcomeBackground = Color(red: 0.043, green: 0.106, blue: 0.169)
    static let welcomeTitle = Color(red: 0.96, green: 0.93, blue: 0.86)
    static let welcomeSubtitle = Color(red: 0.76, green: 0.83, blue: 0.87)
    static let welcomeSprout = Color(red: 0.57, green: 0.65, blue: 0.43)

    // Neutral adaptive surfaces let conference artwork carry the color.
    static let olive = adaptive("Action", light: 0x226478, dark: 0x79C5D2, contrastLight: 0x12465A, contrastDark: 0xB7EFF5)
    static let terracotta = adaptive("Brand", light: 0x226478, dark: 0x79C5D2, contrastLight: 0x12465A, contrastDark: 0xB7EFF5)
    // Filled primary buttons retain white-label contrast in every appearance.
    static let primaryAction = adaptive("PrimaryAction", light: 0x226478, dark: 0x226478, contrastLight: 0x12465A, contrastDark: 0x12465A)
    static let logo = adaptive("Logo", light: 0x226478, dark: 0x79C5D2, contrastLight: 0x12465A, contrastDark: 0xB7EFF5)
    static let fieldBorder = Color(red: 82.0/255, green: 111.0/255, blue: 131.0/255)
    static let fieldFocus = Color(red: 121.0/255, green: 197.0/255, blue: 210.0/255)
    static let buttonSecondary = Color(red: 0.08, green: 0.17, blue: 0.24)
    static let buttonBorder = Color(red: 0.30, green: 0.64, blue: 0.69)
    static let paper = Color(nsColor: .textBackgroundColor)
    static let canvas = Color(nsColor: .windowBackgroundColor)
    static let sage = Color(nsColor: .controlBackgroundColor)
    static let clay = Color(nsColor: .controlBackgroundColor)

    private static func adaptive(_ name: String, light: UInt32, dark: UInt32, contrastLight: UInt32, contrastDark: UInt32) -> Color {
        Color(nsColor: NSColor(name: NSColor.Name("CommonGround.\(name)")) { appearance in
            let match = appearance.bestMatch(from: [.aqua, .darkAqua, .accessibilityHighContrastAqua, .accessibilityHighContrastDarkAqua])
            let hex: UInt32
            switch match {
            case .darkAqua: hex = dark
            case .accessibilityHighContrastAqua: hex = contrastLight
            case .accessibilityHighContrastDarkAqua: hex = contrastDark
            default: hex = light
            }
            return NSColor(srgbRed: CGFloat((hex >> 16) & 255) / 255, green: CGFloat((hex >> 8) & 255) / 255, blue: CGFloat(hex & 255) / 255, alpha: 1)
        })
    }
}

// Shared brand mark used throughout the app.
struct SproutSymbol: Shape {
    func path(in rect: CGRect) -> Path {
        var p = Path()
        p.move(to: CGPoint(x: 0.51, y: 1))
        p.addCurve(to: CGPoint(x: 0.45, y: 0.58), control1: CGPoint(x: 0.53, y: 0.80), control2: CGPoint(x: 0.52, y: 0.67))
        p.addCurve(to: CGPoint(x: 0.02, y: 0.03), control1: CGPoint(x: 0.36, y: 0.43), control2: CGPoint(x: 0.04, y: 0.47))
        p.addCurve(to: CGPoint(x: 0.53, y: 0.65), control1: CGPoint(x: 0.32, y: 0.09), control2: CGPoint(x: 0.51, y: 0.27))
        p.addCurve(to: CGPoint(x: 0.98, y: 0.22), control1: CGPoint(x: 0.59, y: 0.38), control2: CGPoint(x: 0.74, y: 0.24))
        p.addCurve(to: CGPoint(x: 0.62, y: 0.64), control1: CGPoint(x: 0.95, y: 0.45), control2: CGPoint(x: 0.72, y: 0.48))
        p.addCurve(to: CGPoint(x: 0.60, y: 1), control1: CGPoint(x: 0.55, y: 0.75), control2: CGPoint(x: 0.58, y: 0.89))
        p.closeSubpath()
        return p.applying(CGAffineTransform(scaleX: rect.width, y: rect.height))
            .applying(CGAffineTransform(translationX: rect.minX, y: rect.minY))
    }
}
