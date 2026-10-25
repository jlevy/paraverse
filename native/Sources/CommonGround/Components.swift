import SwiftUI

// Shared content components. Native navigation and controls keep system materials.
struct GroundAvatar: View {
    let initials: String
    var isCurrentUser = false
    var body: some View {
        Text(initials).font(.caption.weight(.medium))
            .frame(width: 37, height: 37)
            .background(isCurrentUser ? Brand.sage : Brand.clay, in: Circle())
            .overlay(Circle().stroke(Brand.canvas, lineWidth: 3))
    }
}

struct GroundPlanLink: View {
    let action: () -> Void
    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Image(systemName: "calendar").font(.title2).foregroundStyle(Brand.olive)
                VStack(alignment: .leading, spacing: 5) {
                    Text("Your day, thoughtfully planned").font(.callout.weight(.semibold))
                    Text("Sessions matched to your interests").font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
                Image(systemName: "arrow.up.right")
            }
            .padding(17)
            .background(Brand.paper, in: RoundedRectangle(cornerRadius: 12))
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(.quaternary))
        }.buttonStyle(.plain)
    }
}

struct GroundSectionLabel: View {
    let title: String
    var body: some View {
        Text(title).font(.caption2.weight(.semibold)).tracking(1).foregroundStyle(.secondary)
    }
}

struct ProfileAvatar: View {
    let profile: AttendeeProfile
    var size: CGFloat = 28
    private var cachedImage: NSImage? {
        guard let social = profile.xURL, let handle = URL(string: social)?.path.split(separator: "/").first,
              let url = Bundle.main.url(forResource: "profile-" + handle.lowercased(), withExtension: "jpg") else { return nil }
        return NSImage(contentsOf: url)
    }
    private var fallback: some View {
        Text(profile.initials).font(.system(size: size * 0.36, weight: .semibold))
            .frame(width: size, height: size).background(Brand.sage)
    }
    var body: some View {
        Group {
            if let image = cachedImage {
                Image(nsImage: image).resizable().scaledToFill()
            } else if let value = profile.avatarURL, let url = URL(string: value), url.scheme == "https", url.host == "pbs.twimg.com" {
                CachedRemoteImage(url: url) { fallback }
            } else { fallback }
        }.frame(width: size, height: size).clipShape(Circle()).accessibilityHidden(true)
    }
}

// Paraverse layout decisions, shared across screens (points).
enum GroundLayout {
    static let pageInset: CGFloat = 32
    static let detailWidth: CGFloat = 800
    static let cardInset: CGFloat = 20
    static let sectionGap: CGFloat = 24
    static let cardGap: CGFloat = 20
    static let chatInset: CGFloat = 20
    static let controlHeight: CGFloat = 28
}

struct GroundSidebarLabelStyle: LabelStyle {
    func makeBody(configuration: Configuration) -> some View {
        HStack(spacing: 8) {
            configuration.icon.frame(width: 20, height: 20)
            configuration.title.lineLimit(1)
        }
    }
}


struct SidebarEventCards: View {
    let sessions: [PlannedSession]
    let addToCalendar: ([PlannedSession]) -> Void
    var body: some View {
        ForEach(sessions) { session in
            VStack(alignment: .leading, spacing: 8) {
                Text(session.time).font(.caption.weight(.semibold)).foregroundStyle(Brand.olive)
                Text(session.title).font(.headline)
                Text(session.speakers).font(.subheadline)
                Text(session.location).font(.caption).foregroundStyle(.secondary)
                if !session.reason.isEmpty { Text(session.reason).font(.callout).foregroundStyle(.secondary) }
                HStack {
                    if let url = URL(string: session.sourceURL) { Link("Session details", destination: url) }
                    Spacer()
                    Button("Add to calendar") { addToCalendar([session]) }.buttonStyle(.borderless)
                }.font(.caption)
            }
            .padding(15)
            .background(Brand.paper, in: RoundedRectangle(cornerRadius: 12))
            .accessibilityElement(children: .contain)
        }
    }
}
