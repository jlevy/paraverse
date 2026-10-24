import SwiftUI

/// Only render source-provided profiles on the named platform; never infer handles from names.
struct WorldSocialLinks: View {
    var linkedin: String?
    var x: String?
    var github: String?
    private func profile(_ value: String?, hosts: [String]) -> URL? {
        guard let value, let url = URL(string: value),
              ["https", "http"].contains(url.scheme?.lowercased() ?? ""),
              let host = url.host?.lowercased(), hosts.contains(host),
              !url.path.trimmingCharacters(in: CharacterSet(charactersIn: "/")).isEmpty else { return nil }
        return url
    }
    private var links: [(String, URL)] {
        [("LINKEDIN", profile(linkedin, hosts: ["linkedin.com", "www.linkedin.com"])),
         ("X", profile(x, hosts: ["x.com", "www.x.com", "twitter.com", "www.twitter.com"])),
         ("GITHUB", profile(github, hosts: ["github.com", "www.github.com"]))]
            .compactMap { label, url in url.map { (label, $0) } }
    }
    var body: some View {
        if !links.isEmpty {
            ViewThatFits(in: .horizontal) {
                HStack(spacing: 10) { buttons }
                VStack(alignment: .leading, spacing: 10) { buttons }
            }
        }
    }
    private var buttons: some View {
        ForEach(links, id: \.0) { label, url in
            let title = label == "X" ? "X @" + (url.path.split(separator: "/").first.map(String.init) ?? "") : label
            Link(destination: url) {
                HStack(spacing: 8) {
                    PixelSocialIcon(platform: label)
                    Text(title + " ↗")
                }
            }
                .buttonStyle(PlannerQuietButtonStyle())
                .accessibilityLabel("Open \(title) profile")
        }
    }
}

/// Small grid-drawn marks stay crisp alongside the world's stepped frames.
struct PixelSocialIcon: View {
    let platform: String
    private var pixels: [String] {
        switch platform {
        case "LINKEDIN":
            return [
                "................", "................", "..##............", "..##............",
                "................", "..##..##.###....", "..##..###..##...", "..##..##...##...",
                "..##..##...##...", "..##..##...##...", "..##..##...##...", "..##..##...##...",
                "..##..##...##...", "................", "................", "................"
            ]
        case "GITHUB":
            return [
                "................", "..##........##..", "..####....####..", "..############..",
                ".##############.", ".##############.", ".##############.", "..############..",
                "...##########...", ".....######.....", ".##...####......", "..##..####......",
                "...#######......", "......####......", ".....######.....", "................"
            ]
        default:
            return [
                "................", ".###........##..", "..###......##...", "...###....##....",
                "....###..##.....", ".....#####......", "......###.......", "......####......",
                ".....##.###.....", "....##...###....", "...##.....###...", "..##.......###..",
                ".##.........###.", "................", "................", "................"
            ]
        }
    }
    var body: some View {
        Canvas { context, size in
            let cell = floor(min(size.width, size.height) / 16)
            let origin = CGPoint(x: floor((size.width - cell * 16) / 2), y: floor((size.height - cell * 16) / 2))
            for (row, line) in pixels.enumerated() {
                for (column, pixel) in line.enumerated() where pixel == "#" {
                    context.fill(Path(CGRect(x: origin.x + CGFloat(column) * cell, y: origin.y + CGFloat(row) * cell, width: cell, height: cell)), with: .color(Color(red: 0.99, green: 0.94, blue: 0.81)))
                }
            }
        }.frame(width: 16, height: 16).accessibilityHidden(true)
    }
}
