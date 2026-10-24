import SwiftUI

struct DialogueActionStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled
    let primary: Bool
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 12, weight: .semibold, design: .monospaced))
            .foregroundStyle(primary ? Brand.welcomeTitle : Brand.welcomeSubtitle)
            .padding(.horizontal, 14)
            .frame(minHeight: 44)
            .background(PixelPanel().fill(primary ? Color.teal.opacity(configuration.isPressed ? 0.5 : 0.3) : Color.teal.opacity(configuration.isPressed ? 0.16 : 0.04)))
            .overlay(PixelPanel().stroke(primary ? Brand.buttonBorder : Brand.fieldBorder.opacity(0.6), lineWidth: 1))
            .contentShape(PixelPanel())
            .onChange(of: configuration.isPressed) { _, pressed in
                if pressed && isEnabled { InterfaceSounds.play(primary: primary) }
            }
    }
}
