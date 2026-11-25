#!/usr/bin/env bash
set -euo pipefail

echo "Installing SysMaint (Kennny7 Microservices)..."

# 1. Install package via uv tool (or pipx/pip fallback)
if command -v uv >/dev/null 2>&1; then
    uv tool install --force .
elif command -v pipx >/dev/null 2>&1; then
    pipx install --force .
else
    python3 -m pip install --user --upgrade .
fi

# 2. Ensure ~/.local/bin is in PATH
LOCAL_BIN="$HOME/.local/bin"
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
        if [[ -f "$rc" ]] && ! grep -q '.local/bin' "$rc"; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
        fi
    done
    echo "Added $LOCAL_BIN to PATH in shell profile."
fi

# 3. Install icon and clickable .desktop launcher
ICON_DIR="$HOME/.local/share/icons/hicolor/512x512/apps"
APP_DIR="$HOME/.local/share/applications"
mkdir -p "$ICON_DIR" "$APP_DIR"

cp -f "assets/sysmaint-icon.png" "$ICON_DIR/sysmaint.png"
cp -f "packaging/linux/sysmaint.desktop" "$APP_DIR/sysmaint.desktop"
chmod +x "$APP_DIR/sysmaint.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" || true
fi

echo "Done! You can now launch SysMaint from your Application Menu or run 'sysmaint tui'."
