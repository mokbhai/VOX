"""
Vox - AI-powered text rewriting through macOS contextual menu

Main entry point for the application. Initializes both the menu bar app
and the service provider registration.
"""
import sys
import signal

from vox.ui import MenuBarApp
from vox.service import ServiceProvider


def main():
    """Main entry point for Vox application."""
    # Handle SIGTERM gracefully
    signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))

    # Initialize and register the service provider
    service_provider = ServiceProvider()

    # Initialize and start the menu bar app
    menu_bar_app = MenuBarApp(service_provider)

    # Run the application
    menu_bar_app.run()


if __name__ == "__main__":
    main()
