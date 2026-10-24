import SwiftUI

// Crisp, stepped edges keep UI readable at any zoom level while matching the world.
struct PixelPanel: Shape {
    func path(in r:CGRect)->Path {
        let n:CGFloat=4
        var p=Path()
        p.move(to:CGPoint(x:r.minX+n,y:r.minY))
        for v in [CGPoint(x:r.maxX-n,y:r.minY),CGPoint(x:r.maxX-n,y:r.minY+n),CGPoint(x:r.maxX,y:r.minY+n),CGPoint(x:r.maxX,y:r.maxY-n),CGPoint(x:r.maxX-n,y:r.maxY-n),CGPoint(x:r.maxX-n,y:r.maxY),CGPoint(x:r.minX+n,y:r.maxY),CGPoint(x:r.minX+n,y:r.maxY-n),CGPoint(x:r.minX,y:r.maxY-n),CGPoint(x:r.minX,y:r.minY+n),CGPoint(x:r.minX+n,y:r.minY+n)] {p.addLine(to:v)}
        p.closeSubpath();return p
    }
}
struct WorldButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    var teal = false
    func makeBody(configuration:Configuration)->some View {
        configuration.label
            .font(.system(size:12,weight:.bold,design:.monospaced))
            .foregroundStyle(Color(red:0.99,green:0.94,blue:0.81))
            .padding(.horizontal,14).frame(minHeight:44)
            .background(PixelPanel().fill(teal ? Brand.primaryAction : Brand.buttonSecondary))
            .overlay(PixelPanel().strokeBorderFallback(Brand.buttonBorder))
            .shadow(color:.black.opacity(0.6),radius:0,x:0,y:configuration.isPressed ? 1:4)
            .offset(y:configuration.isPressed ? 3:0)
            .scaleEffect(configuration.isPressed && !reduceMotion ? 0.98 : 1)
            .brightness(configuration.isPressed ? 0.1:0)
            .opacity(isEnabled ? 1 : 0.45)
            .contentShape(Rectangle())
            .animation(reduceMotion ? nil : .easeOut(duration: 0.12), value: configuration.isPressed)
            .onChange(of: configuration.isPressed) { _, pressed in
                if pressed && isEnabled { InterfaceSounds.play(primary: teal) }
            }
    }
}
private extension PixelPanel {
    func strokeBorderFallback(_ color:Color)->some View { stroke(color,lineWidth:2) }
}
struct WorldPlaque<Content:View>: View {
    @ViewBuilder var content:Content
    var body:some View {
        content.padding(14)
            .background(PixelPanel().fill(Color(red:0.12,green:0.15,blue:0.19).opacity(0.96)))
            .overlay(PixelPanel().stroke(Brand.buttonBorder,lineWidth:2))
            .shadow(color:.black.opacity(0.35),radius:0,x:0,y:4)
    }
}

struct PixelPlanet: View {
    // A small sprite grid keeps the silhouette readable at toolbar scale.
    private let rows = [
        "................", ".............mm.", "......tttt...mm.",
        "....tttttttt....", "...tttttttttt...", "...tttttttttt.rr",
        "..ttttttttttrrr.", ".rrtttttttrrr...", "rrttttttrrrtt...",
        "rr.tttrrrtttt...", ".rrrrrrtttttt...", "...ttttttttt....",
        "....ttttttt.....", "......ttt.......", "................", "................"
    ]
    var body: some View {
        Canvas { context, size in
            let unit = min(size.width, size.height) / CGFloat(rows.count)
            for (y, row) in rows.enumerated() {
                for (x, pixel) in row.enumerated() where pixel != "." {
                    let color: Color = pixel == "r" ? Brand.welcomeTitle : pixel == "m" ? Color(red: 0.95, green: 0.68, blue: 0.34) : Color(red: 0.28, green: 0.63, blue: 0.65)
                    context.fill(Path(CGRect(x: CGFloat(x) * unit, y: CGFloat(y) * unit, width: unit, height: unit)), with: .color(color))
                }
            }
        }.accessibilityHidden(true)
    }
}
