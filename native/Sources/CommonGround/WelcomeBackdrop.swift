import AppKit
import SwiftUI

/// Decorative artwork stays separate from the accessible, native welcome controls.
@MainActor
struct WelcomeBackdrop: View {
    private static let artwork = NSImage(contentsOf: worldAsset("WorldArt/ParaverseWelcome.png"))
    var animated = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        GeometryReader { geometry in
            ZStack {
                Brand.welcomeBackground
                if let artwork = Self.artwork {
                    Image(nsImage: artwork)
                        .resizable()
                        .interpolation(.none)
                        .scaledToFill()
                        .frame(width: geometry.size.width, height: geometry.size.height)
                        .clipped()
                }
                if animated && !reduceMotion && scenePhase == .active {
                    LandingAtmosphere()
                }
            }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}

/// A sparse, low-frame-rate ambient layer; the artwork and controls never move.
private struct LandingAtmosphere: View {
    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 12)) { timeline in
            let time = timeline.date.timeIntervalSinceReferenceDate
            Canvas { context, size in
                let glow = CGRect(x: size.width * 0.26, y: size.height * 0.58,
                                  width: size.width * 0.48, height: size.height * 0.48)
                context.fill(Path(ellipseIn: glow), with: .radialGradient(
                    Gradient(colors: [.orange.opacity(0.035 + 0.015 * sin(time * 0.7)), .clear]),
                    center: CGPoint(x: glow.midX, y: glow.midY), startRadius: 0,
                    endRadius: glow.width * 0.5))
                for index in 0..<18 {
                    let seed = Double(index)
                    let progress = (time / (14 + seed.truncatingRemainder(dividingBy: 7)) + seed * 0.137)
                        .truncatingRemainder(dividingBy: 1)
                    let x = size.width * (0.06 + (seed * 0.173).truncatingRemainder(dividingBy: 0.88))
                    let y = size.height * (0.98 - progress * 0.43)
                    let opacity = sin(progress * .pi) * 0.38
                    let pixel = CGRect(x: (x + sin(time * 0.3 + seed) * 6).rounded(),
                                       y: y.rounded(), width: 2, height: 2)
                    context.fill(Path(pixel), with: .color((index.isMultiple(of: 3) ? Color.cyan : .orange).opacity(opacity)))
                }
            }
        }
    }
}

struct LandingPlanet: View {
    var animated: Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 20,
                                paused: !animated || reduceMotion || scenePhase != .active)) { timeline in
            let moving = animated && !reduceMotion && scenePhase == .active
            let offset = moving ? (sin(timeline.date.timeIntervalSinceReferenceDate * .pi / 3) * 4).rounded() : 0
            PixelPlanet().offset(y: offset)
        }
    }
}
