# Vox

AI-powered text rewriting directly in your macOS apps. Select text, right-click, and rewrite instantly.

## What is Vox?

Vox integrates with macOS to add AI-powered text tools to your workflow. Works in any app - Safari, Notes, Mail, Messages, and more.

- **Text Rewriting:** Select text, right-click, and choose from AI rewrite presets (Fix Grammar, Professional, Concise, Friendly)
- **Speech-to-Text:** Press and hold a hotkey to dictate text that gets transcribed locally using Whisper models

## Context Menu Options

When you right-click selected text, you'll see these options under "Rewrite with Vox":

- **Fix Grammar** - Correct spelling, grammar, and punctuation
- **Professional** - Make text formal and business-appropriate
- **Concise** - Shorten text while preserving meaning
- **Friendly** - Make tone warm and casual

The rewritten text replaces your selection instantly. Press Cmd+Z in the host app to undo if needed.

## Features

- Works in any macOS app with text selection
- In-place text replacement (undo with Cmd+Z)
- Global hot keys for quick access (default: ⌘⇧G for Fix Grammar)
- **Offline speech-to-text** using Whisper - dictate text that gets transcribed locally
- Menu bar icon for quick settings access
- API key stored securely in macOS Keychain
- Supports multiple languages

## Installation

1. Build the app using `make build`
2. Copy `dist/Vox.app` to /Applications
3. Run `make flush` to refresh services cache
4. Launch Vox from /Applications
5. Click the "V" menu bar icon and enter your OpenAI API key

## Hot Key

Vox supports a configurable global hot key for quick access:

1. Select text in any app
2. Press the hot key (default: ⌥V)
3. Choose a rewrite style from the picker
4. The rewritten text replaces your selection

To change the shortcut, open Settings from the menu bar icon, click the Shortcut field, and press your desired key combination (e.g. ⌘⇧R). At least one modifier key (⌘, ⌥, ⌃, ⇧) plus a letter or number is required.

**Permissions:** Hot keys require Accessibility and Input Monitoring permissions in System Settings > Privacy & Security.

## Speech-to-Text

Vox includes offline speech recognition using whisper.cpp - dictate text that gets transcribed locally and pasted at your cursor. No internet connection required after the initial model download.

### How to Use

1. Open Preferences → Speech and enable Speech-to-Text
2. Download a model (see Model Options below)
3. Press and hold the speech hotkey (default: fn+F13)
4. Speak into your microphone - you'll see a VU meter showing audio levels
5. Release the hotkey to transcribe
6. The transcribed text is pasted at your cursor

**Customize the hotkey:** In Preferences → Speech, click the Hotkey field and press your desired key combination.

### Model Options

Vox uses Whisper models with varying accuracy and speed trade-offs:

| Model | Size | Accuracy | Speed | Best For |
|-------|------|----------|-------|----------|
| **tiny** | 39MB | Fastest | Lowest | Quick drafts, rough notes |
| **base** | 74MB | Fast | Good | Everyday dictation (recommended) |
| **small** | 244MB | Moderate | Better | Longer recordings, better accuracy |
| **medium** | 769MB | Slower | Best | Important content, maximum accuracy |

Models are downloaded once and stored locally in `~/Library/Application Support/Vox/models/`.

### Languages

Vox supports speech recognition in 12 languages with automatic detection:

- English, Spanish, French, German, Italian, Portuguese
- Russian, Japanese, Korean, Chinese (Simplified), Arabic, Hindi

Select a specific language in Preferences or leave as "Auto-detect" to let Whisper identify the language automatically.

### Permissions

**Microphone access** is required for speech-to-text. When you first use the feature, Vox will prompt you to grant permission in System Settings > Privacy & Security > Microphone.

## Configuration

Access settings from the menu bar icon:

**Settings Tab:**
- API Key - Your OpenAI API key
- Model - Choose gpt-4o, gpt-4o-mini, or others
- Base URL - Custom API endpoint (optional)
- Launch at Login - Auto-start on system boot
- Enable Hot Keys - Toggle the global shortcuts on/off
- Shortcuts - Configure per-mode hotkeys (⌘⇧G for Fix Grammar, etc.)

**Speech Tab:**
- Enable Speech-to-Text - Toggle the speech recognition feature
- Model - Choose the Whisper model size (tiny/base/small/medium)
- Download - Download the selected model (models are 39-769MB)
- Language - Choose a language or use auto-detect
- Hotkey - Configure the press-and-hold recording shortcut

**About Tab:**
- Version information and attribution

## Requirements

macOS 12.0 or later
