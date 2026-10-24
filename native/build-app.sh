#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
swift build -c release
mkdir -p build
swift Tools/GenerateIcon.swift build/Paraverse.iconset
iconutil -c icns build/Paraverse.iconset -o Assets/Paraverse.icns
app="build/Paraverse.app"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
cp Assets/universe-attendees.json "$app/Contents/Resources/universe-attendees.json"
for avatar in Assets/attendee-*.jpg Assets/profile-*.jpg; do
    [ ! -f "$avatar" ] || cp "$avatar" "$app/Contents/Resources/"
done
cp -R Assets/CachedImages "$app/Contents/Resources/"
cp Assets/Paraverse.icns "$app/Contents/Resources/Paraverse.icns"
cp Assets/world-speakers.json "$app/Contents/Resources/"
cp Assets/ptc-judges.json "$app/Contents/Resources/"
cp Assets/browse-events.json "$app/Contents/Resources/"
cp Assets/session-descriptions.json "$app/Contents/Resources/"
cp -R Assets/SpeakerPhotos "$app/Contents/Resources/"
cp -R Assets/WorldArt "$app/Contents/Resources/"
cp Assets/UniverseInterior.png "$app/Contents/Resources/UniverseInterior.png"
cp Assets/WelcomeWoodland.png "$app/Contents/Resources/WelcomeWoodland.png"
cp .build/release/CommonGround "$app/Contents/MacOS/CommonGround"
cat > "$app/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>CommonGround</string>
<key>CFBundleIdentifier</key><string>demo.commonground.mac</string>
<key>CFBundleIconFile</key><string>Paraverse.icns</string>
<key>CFBundleName</key><string>Paraverse</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>0.1.0</string>
<key>CFBundleVersion</key><string>3</string>
<key>LSMinimumSystemVersion</key><string>14.0</string>
<key>NSCalendarsFullAccessUsageDescription</key><string>Paraverse reads your schedule to plan around events and saves calendar changes you choose.</string>
<key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST
# A stable development signature preserves macOS privacy grants across rebuilds.
common_ground_identity="${COMMON_GROUND_SIGNING_IDENTITY:-$(security find-identity -v -p codesigning | awk '/Apple Development:/ {print $2; exit}')}"
codesign --force --sign "${common_ground_identity:--}" "$app"
printf 'Built %s\n' "$PWD/$app"
