#!/bin/bash
set -e

echo "Installing dependencies..."
pip3 install playwright capsolver requests

echo "Installing Chromium browser..."
playwright install chromium

echo "Done! Now:"
echo "  1. Edit config.py with your credentials and class preferences"
echo "  2. Set DRY_RUN = True first to verify it finds the right class"
echo "  3. Run: python3 signup.py"
