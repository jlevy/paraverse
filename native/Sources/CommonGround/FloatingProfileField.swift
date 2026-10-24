import SwiftUI

private struct GameProfileFieldsKey: EnvironmentKey { static let defaultValue = false }
extension EnvironmentValues {
    var gameProfileFields: Bool {
        get { self[GameProfileFieldsKey.self] }
        set { self[GameProfileFieldsKey.self] = newValue }
    }
}
struct FloatingProfileField: View {
    @Environment(\.gameProfileFields) private var gameStyle
    let title: String
    var placeholder = ""
    @Binding var text: String
    var onFocusChange: (Bool) -> Void = { _ in }
    @FocusState private var focused: Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    private var raised: Bool { focused || !text.isEmpty }

    var body: some View {
        ZStack(alignment: .leading) {
            Text(title)
                .font(.system(size: raised ? 11 : 14, weight: gameStyle ? .bold : .regular, design: gameStyle ? .monospaced : .default))
                .foregroundStyle(.secondary)
                .offset(y: raised ? -14 : 0)
                .allowsHitTesting(false)
                .accessibilityHidden(true)
            TextField(title, text: $text, prompt: Text(focused ? placeholder : ""))
                .textFieldStyle(.plain)
                .font(.system(size: 14))
                .padding(.top, 19)
                .focused($focused)
                .accessibilityLabel(title)
        }
        .padding(.horizontal, 14)
        .frame(height: 60)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background {
            if gameStyle { PixelPanel().fill(Color.black.opacity(0.23)) }
            else { RoundedRectangle(cornerRadius:10).fill(Color.primary.opacity(0.035)) }
        }
        .overlay {
            if gameStyle { PixelPanel().stroke(focused ? Brand.fieldFocus : Brand.fieldBorder,lineWidth:focused ? 2 : 1) }
            else { RoundedRectangle(cornerRadius:10).strokeBorder(focused ? Color.accentColor : Color.primary.opacity(0.08),lineWidth:focused ? 2 : 1) }
        }
        .contentShape(RoundedRectangle(cornerRadius: 10))
        .onTapGesture { focused = true }
        .animation(reduceMotion ? nil : .easeOut(duration: 0.15), value: raised)
        .onChange(of: focused) { _, value in onFocusChange(value) }
        .onExitCommand { focused = false }
    }
}
