import SwiftUI
import MapKit

@MainActor @Observable final class CitySuggestions: NSObject, @preconcurrency MKLocalSearchCompleterDelegate {
    var results: [MKLocalSearchCompletion] = []
    var unavailable = false
    private let completer = MKLocalSearchCompleter()

    override init() {
        super.init()
        completer.delegate = self
        completer.resultTypes = .address
        if #available(macOS 15.0, *) {
            completer.addressFilter = MKAddressFilter(including: [.locality])
        }
    }
    func search(_ query: String) {
        unavailable = false
        results = []
        let value = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard value.count >= 2 else { completer.cancel(); return }
        completer.queryFragment = value
    }
    func completerDidUpdateResults(_ completer: MKLocalSearchCompleter) {
        results = Array(completer.results.prefix(5))
    }
    func completer(_ completer: MKLocalSearchCompleter, didFailWithError error: Error) {
        results = []
        unavailable = true
    }
    func stop() { completer.cancel(); results = [] }
}

struct CityField: View {
    @Binding var city: String
    @State private var suggestions = CitySuggestions()
    @State private var focused = false
    @State private var selectedCity: String?

    var body: some View {
        FloatingProfileField(title: "Based in", placeholder: "Search cities", text: $city) { active in
            focused = active
            if active && city != selectedCity { suggestions.search(city) }
            if !active { suggestions.stop() }
        }
        .onChange(of: city) { _, value in
            if focused && value != selectedCity { suggestions.search(value) }
        }
            .overlay(alignment: .top) {
                suggestionPanel
                    .offset(y: 68)
            }
            .onExitCommand { focused = false; suggestions.stop() }
            .onDisappear { suggestions.stop() }
    }

    @ViewBuilder private var suggestionPanel: some View {
            if focused && !suggestions.results.isEmpty {
                VStack(alignment: .leading, spacing: 0) {
                    ForEach(Array(suggestions.results.enumerated()), id: \.offset) { _, result in
                        Button {
                            let value = result.subtitle.isEmpty ? result.title : "\(result.title), \(result.subtitle)"
                            selectedCity = value
                            city = value
                            suggestions.stop()
                        } label: {
                            VStack(alignment: .leading, spacing: 3) {
                                Text(result.title).font(.system(size: 13, weight: .medium))
                                if !result.subtitle.isEmpty {
                                    Text(result.subtitle).font(.caption).foregroundStyle(.secondary)
                                }
                            }.frame(maxWidth: .infinity, alignment: .leading).padding(10).contentShape(Rectangle())
                        }.buttonStyle(.plain)
                    }
                }.background(Color(nsColor: .textBackgroundColor), in: RoundedRectangle(cornerRadius: 10))
                    .overlay(RoundedRectangle(cornerRadius: 10).strokeBorder(Color.primary.opacity(0.1)))
                    .shadow(color: .black.opacity(0.12), radius: 12, y: 4)
                    .fixedSize(horizontal: false, vertical: true)
            }
            if focused && suggestions.unavailable {
                Text("Search unavailable. You can enter your city.").font(.caption).foregroundStyle(.secondary).padding(10).background(Color(nsColor: .textBackgroundColor), in: RoundedRectangle(cornerRadius: 9))
            }
    }
}
