# Vox

AI-powered text rewriting directly in your macOS apps. Select text, right-click, and rewrite instantly.

## What is Vox?

Vox integrates with macOS to add AI text rewriting to your contextual menu. Works in any app - Safari, Notes, Mail, Messages, and more. Just select text and choose how to rewrite it.

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
- Menu bar icon for quick settings access
- API key stored securely in macOS Keychain
- Supports multiple languages

## Installation

1. Build the app using `make build`
2. Copy `dist/Vox.app` to /Applications
3. Run `make flush` to refresh services cache
4. Launch Vox from /Applications
5. Click the "V" menu bar icon and enter your OpenAI API key

## Configuration

Access settings from the menu bar icon:

- API Key - Your OpenAI API key
- Model - Choose gpt-4o, gpt-4o-mini, or others
- Base URL - Custom API endpoint (optional)
- Launch at Login - Auto-start on system boot

## Requirements

macOS 12.0 or later
