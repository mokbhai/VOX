# Vox - Makefile for building and development

.PHONY: all build clean install dev help test lint sync

APP_NAME = Vox
BUILD_DIR = build
DIST_DIR = dist

# Default target
all: build

# Install/sync dependencies with uv
sync:
	uv sync

# Build the .app bundle
build:
	rm -rf $(BUILD_DIR) $(DIST_DIR)
	uv run pyinstaller vox.spec
	@if [ -d "$(DIST_DIR)/$(APP_NAME).app" ]; then \
		echo "Build successful: $(DIST_DIR)/$(APP_NAME).app"; \
	else \
		echo "Build failed!"; \
		exit 1; \
	fi

# Clean build artifacts
clean:
	rm -rf $(BUILD_DIR) $(DIST_DIR) .venv
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.spec" -exec rm -rf {} + 2>/dev/null || true

# Install to /Applications
install: build
	cp -R $(DIST_DIR)/$(APP_NAME).app /Applications/

# Run in development mode (requires pbs -flush after changes)
dev: sync
	uv run python main.py

# Flush services cache (required after service changes)
flush:
	killall cfprefsd 2>/dev/null || true
	/System/Library/CoreServices/pbs -flush

# Run tests
test: sync
	uv run pytest tests/ -v

# Lint code
lint:
	uv run ruff vox/
	uv run mypy vox/

# Format code
fmt:
	uv run ruff format vox/

# Show help
help:
	@echo "Vox - AI-powered text rewriting"
	@echo ""
	@echo "Targets:"
	@echo "  sync     - Install dependencies with uv"
	@echo "  build    - Build the .app bundle (default)"
	@echo "  clean    - Remove build artifacts"
	@echo "  install  - Install to /Applications"
	@echo "  dev      - Run in development mode"
	@echo "  flush    - Flush macOS services cache"
	@echo "  test     - Run tests"
	@echo "  lint     - Lint code"
	@echo "  fmt      - Format code"
	@echo ""
	@echo "Installation:"
	@echo "  make sync && make install && make flush"
