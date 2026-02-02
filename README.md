# Vox

AI-powered text rewriting through macOS contextual menu integration.

## Features

- **Contextual Menu Integration**: Right-click selected text in any app to rewrite
- **Four Rewrite Presets**: Fix Grammar, Professional, Concise, Friendly
- **In-place Replacement**: Text is replaced directly and can be undone (Cmd+Z)
- **Language Detection**: Works with multiple languages, not just English
- **Menu Bar App**: Quick access to settings and configuration
- **Secure Storage**: API key stored in macOS Keychain

## Installation

### Prerequisites

- macOS 12.0+
- [uv](https://github.com/astral-sh/uv) (Python package installer)

### Build from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/vox.git
cd vox

# Install dependencies with uv
uv sync

# Build the .app bundle
make build

# Install to /Applications
cp -R dist/Vox.app /Applications/

# Flush the services cache
make flush
```

### First Run

1. Launch Vox from /Applications
2. Click the "V" icon in the menu bar
3. Select "Set API Key..." and enter your OpenAI API key
4. Optionally change the model in "Model" settings

## Usage

1. Select text in any application (Safari, Notes, Mail, Messages, etc.)
2. Right-click to open the contextual menu
3. Navigate to "Rewrite with Vox" and choose a preset:
   - **Fix Grammar**: Correct spelling, grammar, and punctuation
   - **Professional**: Make text formal and business-appropriate
   - **Concise**: Shorten text while preserving meaning
   - **Friendly**: Make tone warm and casual
4. The text will be replaced with the rewritten version
5. Press Cmd+Z in the host app to undo if needed

## Configuration

Settings are accessible from the menu bar:

- **Set API Key**: Enter or update your OpenAI API key
- **Model**: Choose between gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo
- **Open at Login**: Toggle auto-start at login

Configuration is stored in:
- `~/Library/Application Support/Vox/config.yml`
- macOS Keychain (for API key)

## Development

```bash
# Install/sync dependencies
uv sync

# Run in development mode
make dev

# Run tests
make test

# Lint code
make lint

# Format code
make fmt

# Build for distribution
make build

# Clean build artifacts
make clean
```

## Requirements

See `pyproject.toml` for full dependency list:
- PyObjC for macOS native API integration
- OpenAI Python SDK for text processing
- py2app for creating .app bundles

## License

MIT License
