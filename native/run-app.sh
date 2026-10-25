#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
bash build-app.sh
# Quit all packaged copies before opening the exact Knowledge Base build.
swift -e '
import AppKit
let copies = NSWorkspace.shared.runningApplications.filter {
    ["Paraverse.app", "Paraverse Final.app"].contains($0.bundleURL?.lastPathComponent ?? "") && $0.executableURL?.lastPathComponent == "CommonGround"
}
for app in copies { app.terminate() }
let deadline = Date().addingTimeInterval(10)
while copies.contains(where: { !$0.isTerminated }) && Date() < deadline { RunLoop.current.run(until: Date().addingTimeInterval(0.1)) }
if copies.contains(where: { !$0.isTerminated }) { fputs("A Paraverse copy is still closing. Launch cancelled to avoid duplicates.\n", stderr); exit(1) }
'
open "$PWD/build/Paraverse Final.app"
