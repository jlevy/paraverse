import SwiftUI

/// Short, interruptible page changes based on Emil's ease-out motion guidance.
struct FlowTransition: ViewModifier {
    let step: Int
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func body(content: Content) -> some View {
        ZStack {
            content
                .id(step)
                .transition(reduceMotion ? .identity : .asymmetric(
                    insertion: .opacity.combined(with: .offset(y: 12)),
                    removal: .opacity.combined(with: .offset(y: -8))
                ))
        }
        .clipped()
        .animation(reduceMotion ? nil : .timingCurve(0.215, 0.61, 0.355, 1, duration: 0.24), value: step)
    }
}
