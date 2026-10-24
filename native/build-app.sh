#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
graph_python="../db/.venv/bin/python"
if [ ! -x "$graph_python" ]; then
    printf 'Install the knowledge-base runtime first: run make install in db/.\n' >&2
    exit 1
fi
PYTHONPATH="../db/src" "$graph_python" ../backend/export_kb_native.py --reuse-validation
swift build -c release
mkdir -p build
swift Tools/GenerateIcon.swift build/Paraverse.iconset
iconutil -c icns build/Paraverse.iconset -o Assets/Paraverse.icns
app="build/Paraverse.app"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
python3 ../backend/export_public_attendees.py Assets/universe-attendees.json "$app/Contents/Resources/universe-attendees.json"
for avatar in Assets/attendee-*.jpg Assets/profile-*.jpg; do
    [ ! -f "$avatar" ] || cp "$avatar" "$app/Contents/Resources/"
done
cp -R Assets/CachedImages "$app/Contents/Resources/"
cp Assets/Paraverse.icns "$app/Contents/Resources/Paraverse.icns"
cp Assets/world-speakers.json "$app/Contents/Resources/"
cp Assets/ptc-judges.json "$app/Contents/Resources/"
cp Assets/kb-sessions.json Assets/kb-attendees.json Assets/kb-native-manifest.json "$app/Contents/Resources/"
cp Assets/browse-events.json "$app/Contents/Resources/"
cp Assets/session-descriptions.json "$app/Contents/Resources/"
cp -R Assets/SpeakerPhotos "$app/Contents/Resources/"
cp -R Assets/WorldArt "$app/Contents/Resources/"
cp Assets/UniverseInterior.png "$app/Contents/Resources/UniverseInterior.png"
cp Assets/WelcomeWoodland.png "$app/Contents/Resources/WelcomeWoodland.png"
cp .build/release/CommonGround "$app/Contents/MacOS/CommonGround"
"$graph_python" - "$app/Contents/Resources/ParaverseBuild.json" <<'BUILD_INFO'
import hashlib, json, pathlib, subprocess, sys
manifest = pathlib.Path('Assets/kb-native-manifest.json').read_bytes()
revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
branch = subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip()
dirty = bool(subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no']))
pathlib.Path(sys.argv[1]).write_text(json.dumps(dict(sourceRevision=revision, sourceBranch=branch, sourceDirty=dirty, kbManifestSha256=hashlib.sha256(manifest).hexdigest()), indent=2) + '\n')
BUILD_INFO
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
