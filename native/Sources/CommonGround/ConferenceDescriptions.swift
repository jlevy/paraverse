import Foundation

extension ConferenceRecord {
    var discoveryTitle: String {
        switch id {
        case "qcon-sf-2026": return "Qcon"
        case "sf-ruby-2026": return "Ruby Conference"
        default: return title
        }
    }

    /// Condensed from official organizer pages, checked October 24, 2026.
    var discoverySummary: String {
        switch id {
        case "universe-2026":
            // https://githubuniverse.com/
            return "GitHub’s flagship event for developers building with AI and agents."
        case "qcon-sf-2026":
            // https://qconsf.com/
            return "Production lessons in AI and software, shared by senior engineers."
        case "portcon-2026":
            // https://portcon.port.io/
            return "The AI Software Factory Summit: scaling from prototype to production."
        case "sf-ruby-2026":
            // https://sfruby.com/
            return "Ruby’s next chapter: AI, Rails, and conversations with fellow builders."
        case "atlassian-team-2027":
            // https://events.atlassian.com/team
            return "Atlassian’s teamwork event: connect, learn, and grow with your peers."
        case "stripe-sessions-2027":
            // https://stripesessions.com/
            return "Stripe’s internet economy conference on AI, commerce, and global growth."
        default:
            return program.isEmpty ? themes.joined(separator: ", ") : program
        }
    }
}
