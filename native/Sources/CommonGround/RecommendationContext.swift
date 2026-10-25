import SwiftUI

struct RecommendationContext: View {
    let about: String?

    var body: some View {
        if let about, !about.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            VStack(alignment: .leading, spacing: 6) {
                Text("About").font(.system(size: 12, weight: .semibold))
                Text(about).font(.system(size: 13)).lineSpacing(3).lineLimit(3)
            }
            .foregroundStyle(Brand.welcomeSubtitle)
        }
    }
}

struct RecommendationReason: View {
    let reason: String
    var body: some View {
        if !reason.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            VStack(alignment: .leading, spacing: 6) {
                Text("Why this fits you")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(Color(red: 0.47, green: 0.77, blue: 0.82))
                Text(.init(reason.replacingOccurrences(of: "—", with: ", ").replacingOccurrences(of: " ,", with: ",").replacingOccurrences(of: "  ", with: " "))).font(.system(size: 13)).lineSpacing(3)
                    .foregroundStyle(Brand.welcomeTitle)
                    .fixedSize(horizontal: false, vertical: true)
                    .textSelection(.enabled)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}
