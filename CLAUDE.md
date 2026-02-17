# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vox is a macOS menu bar application that provides AI-powered text rewriting through contextual menu integration. Users select text in any macOS app, right-click, and choose from AI rewrite presets (Fix Grammar, Professional, Concise, Friendly). The rewritten text replaces the selection in-place.

## Architecture

### Core Modules

- **`vox/main.py`** - Entry point; initializes both the menu bar app and service provider registration
- **`vox/service.py`** - macOS Services API integration via PyObjC; receives text from contextual menu and processes it
- **`vox/ui.py`** - Menu bar app with settings dialog; handles text selection/paste simulation using CGEvent; shows mode picker dialog; includes `EditableTextField` (fixes Cmd+C/V/X/A in NSAlert modals) and `HotkeyRecorderField` (captures keyboard shortcuts)
- **`vox/api.py`** - OpenAI API client; defines rewrite modes with system prompts; supports custom base URLs
- **`vox/config.py`** - Configuration management; stores settings in `~/Library/Application Support/Vox/config.yml`
- **`vox/notifications.py`** - Toast popups near cursor for loading state; macOS notification banners for errors
- **`vox/hotkey.py`** - Global hot key handling using Quartz CGEventTap; requires Accessibility permission; includes display helpers (`format_hotkey_display`, `modifier_mask_to_string`) for symbol-formatted shortcuts

### Data Flow

**Context Menu Flow**: User selects text → Right-click → "Rewrite with Vox" → Choose mode → `ServiceProvider` receives text via pasteboard → API call → Replace text in pasteboard → Toast notification

**Hot Key Flow**: User presses configured hot key with text selected → `HotKeyManager` detects → Simulates Cmd+C → Shows mode picker → Processes text → Simulates Cmd+V

### macOS Integration

- **Services API**: Registered via NSServices in `vox.spec`; appears in contextual menu across all apps
- **PyObjC**: Uses PyObjC for native macOS APIs (Cocoa, Quartz)
- **Permissions**: Accessibility required for global hot keys; Notification required for error banners
- **Auto-start**: Managed via Launch Agent at `~/Library/LaunchAgents/com.voxapp.rewrite.plist`

## Package Manager

Always use `uv` for Python package management:

```bash
# Install/sync dependencies
uv sync

# Run commands
uv run python main.py
uv run pytest tests/ -v
uv run ruff vox/

# Add packages
uv add <package>
uv add --dev <package>
```

## Commands

```bash
# Install dependencies
make sync  (alias for uv sync)

# Build the .app bundle
make build

# Install to /Applications
make install

# Run in development mode
make dev

# Flush services cache (required after service changes)
make flush

# Run tests
make test

# Lint code
make lint

# Format code
make fmt
```

## Development Notes

- After modifying service-related code, run `make flush` to refresh the macOS services cache
- Service may take 1-2 seconds to appear after first install
- The app runs with `LSUIElement: True` (no dock icon, only menu bar)
- Bundle identifier: `com.voxapp.rewrite`
