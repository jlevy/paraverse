import AppKit

@MainActor enum InterfaceSounds {
    static let preferenceKey = "paraverse.interfaceSoundsMuted"
    private static let click = makeSound(notes: [660], noteDuration: 0.055)
    private static let advance = makeSound(notes: [660, 880], noteDuration: 0.055)

    static func play(primary: Bool) {
        guard !UserDefaults.standard.bool(forKey: preferenceKey) else { return }
        click?.stop()
        advance?.stop()
        let sound = primary ? advance : click
        sound?.volume = 0.22
        sound?.play()
    }

    // Original, short triangle-wave cues with soft edges to avoid speaker clicks.
    private static func makeSound(notes: [Double], noteDuration: Double) -> NSSound? {
        let sampleRate = 22_050
        let samplesPerNote = Int(Double(sampleRate) * noteDuration)
        var pcm = Data()
        for frequency in notes {
            for index in 0..<samplesPerNote {
                let time = Double(index) / Double(sampleRate)
                let envelope = min(1, time / 0.005) * max(0, 1 - time / noteDuration)
                let wave = 2 / Double.pi * asin(sin(2 * .pi * frequency * time))
                var sample = Int16(wave * envelope * 16_000).littleEndian
                withUnsafeBytes(of: &sample) { pcm.append(contentsOf: $0) }
            }
        }
        var wav = Data()
        func text(_ value: String) { wav.append(contentsOf: value.utf8) }
        func number<T: FixedWidthInteger>(_ value: T) {
            var littleEndian = value.littleEndian
            withUnsafeBytes(of: &littleEndian) { wav.append(contentsOf: $0) }
        }
        text("RIFF"); number(UInt32(36 + pcm.count)); text("WAVEfmt ")
        number(UInt32(16)); number(UInt16(1)); number(UInt16(1))
        number(UInt32(sampleRate)); number(UInt32(sampleRate * 2))
        number(UInt16(2)); number(UInt16(16))
        text("data"); number(UInt32(pcm.count)); wav.append(pcm)
        return NSSound(data: wav)
    }
}
