import SwiftUI

struct PublicAttendee: Decodable, Identifiable {
    let name, username, attendance_mode, evidence, source_url, profile_url, post_date: String
    let matching_opt_in: Bool
    var role: String?
    var about: String?
    var interests: [InterestSuggestion]?
    var linkedin_url: String?
    var github_url: String?
    var avatar_asset: String?
    var avatarImage: NSImage? {
        guard let name = avatar_asset, let url = Bundle.main.url(forResource: name, withExtension: "jpg") else { return nil }
        return NSImage(contentsOf: url)
    }
    var id: String { username }
    var initials: String { name.split(separator: " ").prefix(2).compactMap(\.first).map(String.init).joined() }
    var attendanceLabel: String { attendance_mode == "in_person" ? "In person" : "Format not specified" }
    static func load() throws -> [PublicAttendee] {
        guard let url = Bundle.main.url(forResource: "kb-attendees", withExtension: "json") else { throw CocoaError(.fileNoSuchFile) }
        return try JSONDecoder().decode([PublicAttendee].self, from: Data(contentsOf: url))
    }
}
struct AttendeesPage: View {
    @State private var people: [PublicAttendee] = []
    @State private var query = ""
    @State private var inPersonOnly = false
    @State private var loadFailed = false
    var filtered: [PublicAttendee] { people.filter { (!inPersonOnly || $0.attendance_mode == "in_person") && (query.isEmpty || ($0.name + " " + $0.username + " " + ($0.role ?? "")).localizedCaseInsensitiveContains(query)) } }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: GroundLayout.sectionGap) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("See who’s going.").font(.system(size: 28, weight: .semibold, design: .default))
                    Text("GitHub Universe · October 28–29").foregroundStyle(.secondary)
                    Text("Public attendance announcements. Group matching starts when people opt in.").font(.callout).foregroundStyle(.secondary)
                }
                HStack(spacing: 16) {
                    TextField("Search people or roles", text: $query).textFieldStyle(.roundedBorder)
                    Toggle("In person", isOn: $inPersonOnly).toggleStyle(.checkbox)
                }
                Text("\(filtered.count) people").font(.caption).foregroundStyle(.secondary)
                if loadFailed { ContentUnavailableView("Couldn’t load attendees", systemImage: "person.2", description: Text("Reopen the app to try again.")) }
                else if filtered.isEmpty { ContentUnavailableView.search(text: query) }
                ForEach(filtered) { person in
                    VStack(alignment: .leading, spacing: 14) {
                        HStack(alignment: .top, spacing: 14) {
                            Group {
                                if let image = person.avatarImage {
                                    Image(nsImage: image).resizable().scaledToFill()
                                } else {
                                    Text(person.initials).font(.headline).foregroundStyle(Brand.olive)
                                }
                            }.frame(width: 44, height: 44).background(Brand.sage).clipShape(Circle()).accessibilityHidden(true)
                            VStack(alignment: .leading, spacing: 5) {
                                Text(person.name).font(.headline)
                                if let role = person.role { Text(role).font(.callout).foregroundStyle(.secondary) }
                                Text("@\(person.username)").font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Text(person.attendanceLabel).font(.caption).padding(.horizontal, 10).padding(.vertical, 6).background(Brand.sage.opacity(0.5), in: Capsule())
                        }
                        if let about = person.about, !about.isEmpty { Text(about).font(.callout).foregroundStyle(.secondary) }
                        if let interests = person.interests, !interests.isEmpty {
                            DisclosureGroup("Interests & sources") {
                                VStack(alignment: .leading, spacing: 12) {
                                    ForEach(interests) { interest in
                                        VStack(alignment: .leading, spacing: 4) {
                                            Text(interest.label).font(.callout.weight(.medium))
                                            Text(interest.category == "personal" ? "Outside work" : "Work").font(.caption).foregroundStyle(.secondary)
                                            Text(interest.reason).font(.caption).foregroundStyle(.secondary)
                                            if let url = interest.sourceURL { Link("View source", destination: url).font(.caption) }
                                        }
                                    }
                                }.padding(.top, 10)
                            }
                        }
                        HStack {
                            if let url = URL(string: person.profile_url) { Link("View profile", destination: url) }
                            if let value = person.linkedin_url, let url = URL(string: value) { Link("LinkedIn", destination: url) }
                        }.font(.callout)
                        DisclosureGroup("Attendance announcement") {
                            VStack(alignment: .leading, spacing: 10) {
                                Text(person.evidence).font(.callout).textSelection(.enabled)
                                Text("Observed \(String(person.post_date.prefix(10))) · Public attendance evidence").font(.caption).foregroundStyle(.secondary)
                                HStack {
                                    if let url = URL(string: person.source_url) { Link("View announcement", destination: url) }
                                    if let url = URL(string: person.profile_url) { Link("View profile", destination: url) }
                                }.font(.callout)
                            }.padding(.top, 10)
                        }
                    }.padding(GroundLayout.cardInset).frame(maxWidth: .infinity, alignment: .leading).background(Brand.paper, in: RoundedRectangle(cornerRadius: 12)).overlay(RoundedRectangle(cornerRadius: 12).stroke(.quaternary, lineWidth: 1))
                }
            }.padding(GroundLayout.pageInset).frame(maxWidth: GroundLayout.detailWidth, alignment: .leading).frame(maxWidth: .infinity)
        }.background(Brand.canvas)
        .task { do { people = try PublicAttendee.load() } catch { loadFailed = true } }
    }
}

struct MeetPersonCard: View {
    let person: PersonRecommendation
    var gameStyle = false
    var showReason = true
    private var avatar: NSImage? {
        guard let asset = person.avatarAsset,
              let url = Bundle.main.url(forResource: asset, withExtension: "jpg") else { return nil }
        return NSImage(contentsOf: url)
    }
    var body: some View {
        if gameStyle { gameCard } else { standardCard }
    }
    private var standardCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .center, spacing: 12) {
                Group {
                    if let avatar { Image(nsImage: avatar).resizable().scaledToFill() }
                    else { Text(person.name.split(separator: " ").prefix(2).compactMap(\.first).map(String.init).joined()).font(.headline) }
                }.frame(width: 44, height: 44).background(Brand.sage).clipShape(Circle()).accessibilityHidden(true)
                VStack(alignment: .leading, spacing: 4) {
                    Text(person.name).font(.headline)
                    Text(person.role).font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 0)
            }
            Text(.init(person.reason)).font(.callout).lineSpacing(3).fixedSize(horizontal: false, vertical: true).textSelection(.enabled)
            HStack(spacing: 16) {
                if let url = URL(string: person.profileURL) { Link("View profile", destination: url) }
                if let url = URL(string: person.sourceURL) { Link("Attendance post", destination: url) }
            }.font(.caption).frame(minHeight: GroundLayout.controlHeight)
        }.padding(16).frame(maxWidth: .infinity, alignment: .leading)
            .background(Brand.paper, in: RoundedRectangle(cornerRadius: 12))
            .overlay(RoundedRectangle(cornerRadius: 12).strokeBorder(.quaternary))
    }
}

private extension MeetPersonCard {
    var pixelAvatar: NSImage? {
        WorldCharacter.recommendationImage(for: person.personID)
    }
    var attendee: PublicAttendee? { (try? PublicAttendee.load())?.first { $0.id == person.personID || $0.profile_url == person.profileURL } }
    var gameCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            if showReason { RecommendationReason(reason: person.reason) }
        VStack(alignment: .leading, spacing: 20) {
            HStack(alignment: .center, spacing: 16) {
                Group {
                    if let pixelAvatar {
                        Image(nsImage: pixelAvatar).resizable().interpolation(.none).scaledToFit()
                    } else {
                        Text(person.name.split(separator: " ").prefix(2).compactMap(\.first).map(String.init).joined())
                            .font(.system(size: 18, weight: .bold, design: .monospaced))
                    }
                }
                .frame(width: 64, height: 72)
                .background(Brand.buttonSecondary)
                .clipShape(PixelPanel())
                .accessibilityHidden(true)
                VStack(alignment: .leading, spacing: 6) {
                    Text(person.name).font(.system(size: 18, weight: .bold, design: .monospaced))
                    if !person.role.isEmpty {
                        Text(person.role).font(.system(size: 13)).foregroundStyle(Brand.welcomeSubtitle)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                Spacer(minLength: 0)
            }
            RecommendationContext(about: attendee?.about ?? WorldSpeaker.all.first(where: { $0.id == person.personID })?.biography ?? person.role)
            ViewThatFits(in: .horizontal) {
                HStack(spacing: 8) { gameLinks }
                VStack(alignment: .leading, spacing: 4) { gameLinks }
            }
        }
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .foregroundStyle(Brand.welcomeTitle)
        .background(PixelPanel().fill(Color(red: 0.12, green: 0.15, blue: 0.19)))
        .overlay(PixelPanel().stroke(Brand.fieldBorder, lineWidth: 1))
        }
        .padding(.bottom, 8)
    }
    var cardLinks: [(String, URL)] {
        let candidates: [(String, String?)] = [
            ("LinkedIn", person.linkedinURL ?? attendee?.linkedin_url),
            ("X", person.xURL),
            ("GitHub", person.githubURL ?? attendee?.github_url),
            ("Profile", person.profileURL),
            ("Attendance post", person.sourceURL)
        ]
        var seen = Set<String>()
        return candidates.compactMap { title, value in
            guard let value, let url = URL(string: value),
                  ["https", "http"].contains(url.scheme?.lowercased() ?? ""),
                  let host = url.host?.lowercased() else { return nil }
            let canonicalHost = host.replacingOccurrences(of: "www.", with: "").replacingOccurrences(of: "twitter.com", with: "x.com")
            let key = canonicalHost + url.path.trimmingCharacters(in: CharacterSet(charactersIn: "/")).lowercased()
            guard seen.insert(key).inserted else { return nil }
            return (title, url)
        }
    }
    var gameLinks: some View {
        ForEach(cardLinks, id: \.0) { title, url in
            Link(destination: url) {
                HStack(spacing: 8) {
                    if ["LinkedIn", "X", "GitHub"].contains(title) {
                        PixelSocialIcon(platform: title.uppercased())
                    } else {
                        Image(systemName: "arrow.up.right")
                    }
                    Text(title)
                }
            }
                .buttonStyle(PlannerQuietButtonStyle())
        }
    }
}
