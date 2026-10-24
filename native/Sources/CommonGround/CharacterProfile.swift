import SwiftUI

struct CharacterProfile: Decodable {
    struct Source: Decodable, Hashable {
        let title: String
        let url: URL
    }
    struct Section: Decodable {
        let title, body: String
        let sources: [Source]
    }
    let personID, reviewedAt, summary: String
    let sections: [Section]

    static let all: [CharacterProfile] = (try? JSONDecoder().decode(
        [CharacterProfile].self, from: Data(contentsOf: worldAsset("character-profiles.json"))
    )) ?? []

    static func find(_ personID: String) -> CharacterProfile? {
        all.first { $0.personID == personID }
    }
}

struct CharacterProfileDetails: View {
    let profile: CharacterProfile
    var body: some View {
        VStack(alignment: .leading, spacing: 22) {
            Text(profile.summary).font(.headline)
            ForEach(profile.sections.indices, id: \.self) { index in
                let section = profile.sections[index]
                VStack(alignment: .leading, spacing: 8) {
                    Text(section.title).font(.headline).foregroundStyle(Brand.welcomeSubtitle)
                    Text(section.body).textSelection(.enabled)
                    ForEach(section.sources, id: \.self) { source in
                        Link(source.title + " ↗", destination: source.url).font(.caption)
                    }
                }
            }
            Text("Public sources reviewed " + profile.reviewedAt).font(.caption).foregroundStyle(.secondary)
        }.frame(maxWidth: .infinity, alignment: .leading)
    }
}
