import AppKit

// Package the approved pixel planet artwork at all macOS Dock/Finder sizes.
let destination = URL(fileURLWithPath: CommandLine.arguments[1])
let source = URL(fileURLWithPath: "Assets/ParaverseIcon.png")
guard let image = NSImage(contentsOf: source) else {
    fatalError("Missing Paraverse icon artwork at \(source.path)")
}
try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true)
let iconPointSizes = [16, 32, 128, 256, 512]
let displayScales = [1, 2]
for points in iconPointSizes {
    for scale in displayScales {
        let pixels = points * scale
        let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: pixels, pixelsHigh: pixels, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
        NSGraphicsContext.current?.imageInterpolation = .none
        image.draw(in: NSRect(x: 0, y: 0, width: pixels, height: pixels), from: .zero, operation: .copy, fraction: 1)
        NSGraphicsContext.restoreGraphicsState()
        let suffix = scale == 2 ? "@2x" : ""
        try bitmap.representation(using: .png, properties: [:])!.write(to: destination.appendingPathComponent("icon_\(points)x\(points)\(suffix).png"))
    }
}
