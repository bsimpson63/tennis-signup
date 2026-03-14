#!/bin/bash
set -e

echo "Installing dependencies..."
pip3 install playwright capsolver requests

echo "Installing Chromium browser..."
playwright install chromium

echo "Generating launchd plist..."
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON3="$(which python3)"

cat > "$PROJECT_DIR/com.tennis-signup.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tennis-signup</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON3</string>
        <string>$PROJECT_DIR/signup.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>0</integer>
        <key>Minute</key>
        <integer>1</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/signup.log</string>

    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/signup.log</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

echo "Generated com.tennis-signup.plist"
echo ""
echo "Done! Next steps:"
echo "  1. Copy .env.example to .env and fill in your credentials"
echo "  2. Run: python3 signup.py (with DRY_RUN = True to verify)"
echo "  3. To schedule nightly runs:"
echo "     cp com.tennis-signup.plist ~/Library/LaunchAgents/"
echo "     launchctl bootstrap gui/\$(id -u) ~/Library/LaunchAgents/com.tennis-signup.plist"
