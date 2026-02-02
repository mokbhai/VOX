"""
Menu bar application for Vox.

Provides a menu bar icon with access to settings and configuration.
"""
import objc
import AppKit
import Foundation
from PyObjCTools import AppHelper
from typing import Optional

from vox.config import get_config
from vox.api import RewriteMode
from vox.service import ServiceProvider


def show_settings_dialog(callback, config):
    """Show settings dialog using NSAlert with custom view."""
    alert = AppKit.NSAlert.alloc().init()
    alert.setMessageText_("Vox Settings")
    alert.setInformativeText_("Configure your OpenAI settings below.")
    alert.setAlertStyle_(AppKit.NSAlertStyleInformational)

    # Get current values
    current_key = config.get_api_key() or ""
    current_model = config.model or "gpt-4o-mini"
    current_url = config.base_url or ""
    current_auto_start = config.auto_start

    # Create container for all fields
    container = AppKit.NSView.alloc().initWithFrame_(
        Foundation.NSMakeRect(0, 0, 380, 220)
    )

    y_offset = 200

    # API Key
    api_label = AppKit.NSTextField.alloc().initWithFrame_(
        Foundation.NSMakeRect(0, y_offset, 100, 20)
    )
    api_label.setStringValue_("API Key:")
    api_label.setBezeled_(False)
    api_label.setDrawsBackground_(False)
    api_label.setEditable_(False)
    api_label.setSelectable_(False)
    api_label.setAlignment_(AppKit.NSTextAlignmentRight)
    container.addSubview_(api_label)

    api_field = AppKit.NSTextField.alloc().initWithFrame_(
        Foundation.NSMakeRect(110, y_offset, 260, 24)
    )
    api_field.setStringValue_(current_key)
    api_field.setPlaceholderString_("sk-...")
    api_field.setEditable_(True)
    api_field.setSelectable_(True)
    container.addSubview_(api_field)

    y_offset -= 35

    # Model
    model_label = AppKit.NSTextField.alloc().initWithFrame_(
        Foundation.NSMakeRect(0, y_offset, 100, 20)
    )
    model_label.setStringValue_("Model:")
    model_label.setBezeled_(False)
    model_label.setDrawsBackground_(False)
    model_label.setEditable_(False)
    model_label.setSelectable_(False)
    model_label.setAlignment_(AppKit.NSTextAlignmentRight)
    container.addSubview_(model_label)

    model_field = AppKit.NSTextField.alloc().initWithFrame_(
        Foundation.NSMakeRect(110, y_offset, 260, 24)
    )
    model_field.setStringValue_(current_model)
    model_field.setPlaceholderString_("gpt-4o-mini")
    model_field.setEditable_(True)
    model_field.setSelectable_(True)
    container.addSubview_(model_field)

    y_offset -= 35

    # Base URL
    url_label = AppKit.NSTextField.alloc().initWithFrame_(
        Foundation.NSMakeRect(0, y_offset, 100, 20)
    )
    url_label.setStringValue_("Base URL:")
    url_label.setBezeled_(False)
    url_label.setDrawsBackground_(False)
    url_label.setEditable_(False)
    url_label.setSelectable_(False)
    url_label.setAlignment_(AppKit.NSTextAlignmentRight)
    container.addSubview_(url_label)

    url_field = AppKit.NSTextField.alloc().initWithFrame_(
        Foundation.NSMakeRect(110, y_offset, 260, 24)
    )
    url_field.setStringValue_(current_url)
    url_field.setPlaceholderString_("https://api.openai.com/v1")
    url_field.setEditable_(True)
    url_field.setSelectable_(True)
    container.addSubview_(url_field)

    y_offset -= 35

    # Launch at login checkbox
    auto_label = AppKit.NSTextField.alloc().initWithFrame_(
        Foundation.NSMakeRect(0, y_offset, 100, 20)
    )
    auto_label.setStringValue_("Startup:")
    auto_label.setBezeled_(False)
    auto_label.setDrawsBackground_(False)
    auto_label.setEditable_(False)
    auto_label.setSelectable_(False)
    auto_label.setAlignment_(AppKit.NSTextAlignmentRight)
    container.addSubview_(auto_label)

    auto_checkbox = AppKit.NSButton.alloc().initWithFrame_(
        Foundation.NSMakeRect(110, y_offset - 2, 150, 25)
    )
    auto_checkbox.setButtonType_(AppKit.NSSwitchButton)
    auto_checkbox.setTitle_("Launch at login")
    auto_checkbox.setState_(AppKit.NSControlStateValueOn if current_auto_start else AppKit.NSControlStateValueOff)
    container.addSubview_(auto_checkbox)

    alert.setAccessoryView_(container)

    alert.addButtonWithTitle_("Save")
    alert.addButtonWithTitle_("Cancel")

    # Activate app first
    AppKit.NSApp.activateIgnoringOtherApps_(True)

    response = alert.runModal()

    if response == AppKit.NSAlertFirstButtonReturn:
        api_key = api_field.stringValue().strip()
        model = model_field.stringValue().strip() or "gpt-4o-mini"
        base_url = url_field.stringValue().strip() or None
        auto_start = auto_checkbox.state() == AppKit.NSControlStateValueOn

        if callback:
            callback(api_key, model, base_url, auto_start)


def show_about_dialog():
    """Show about dialog."""
    alert = AppKit.NSAlert.alloc().init()
    alert.setMessageText_("Vox")
    alert.setInformativeText_(
        "AI-powered text rewriting through macOS contextual menu.\n\n"
        "Version 0.1.0\n\n"
        "Right-click any text to rewrite with AI."
    )
    alert.setAlertStyle_(AppKit.NSAlertStyleInformational)
    alert.addButtonWithTitle_("OK")
    AppKit.NSApp.activateIgnoringOtherApps_(True)
    alert.runModal()


class MenuBarActions(AppKit.NSObject):
    """Simple object to handle menu actions."""

    def init(self):
        """Initialize."""
        self = objc.super(MenuBarActions, self).init()
        self.app = None  # Reference to MenuBarApp
        return self

    def showSettings_(self, sender):
        """Show settings."""
        print("DEBUG: showSettings called")
        if self.app:
            self.app._show_settings()

    def showAbout_(self, sender):
        """Show about."""
        print("DEBUG: showAbout called")
        if self.app:
            self.app._show_about()

    def quit_(self, sender):
        """Quit."""
        print("DEBUG: quit called")
        if self.app:
            self.app._quit()


class MenuBarApp:
    """Main menu bar application for Vox."""

    def __init__(self, service_provider: ServiceProvider):
        """
        Initialize the menu bar app.

        Args:
            service_provider: The service provider instance.
        """
        self.service_provider = service_provider
        self.config = get_config()

        # Create the application
        self.app = AppKit.NSApplication.sharedApplication()
        self.app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

        # Create actions object (proper NSObject subclass for selectors)
        self.actions = MenuBarActions.alloc().init()
        self.actions.app = self

        # Create status item
        self._create_status_item()
        self._create_menu()

    def _create_status_item(self):
        """Create the status item in the menu bar."""
        status_bar = AppKit.NSStatusBar.systemStatusBar()
        self.status_item = status_bar.statusItemWithLength_(AppKit.NSVariableStatusItemLength)

        # Set icon (using a simple text icon for now)
        self.status_item.setTitle_("V")

        # Create menu
        self.menu = AppKit.NSMenu.alloc().init()
        self.status_item.setMenu_(self.menu)

    def _create_menu(self):
        """Create the menu items."""
        self.menu.removeAllItems()

        # Settings
        settings_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Settings...", "showSettings:", ""
        )
        settings_item.setTarget_(self.actions)
        self.menu.addItem_(settings_item)

        # Separator
        self.menu.addItem_(AppKit.NSMenuItem.separatorItem())

        # About
        about_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "About Vox", "showAbout:", ""
        )
        about_item.setTarget_(self.actions)
        self.menu.addItem_(about_item)

        # Separator
        self.menu.addItem_(AppKit.NSMenuItem.separatorItem())

        # Quit
        quit_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit Vox", "quit:", "q"
        )
        quit_item.setTarget_(self.actions)
        self.menu.addItem_(quit_item)

    def _show_settings(self):
        """Show the settings dialog."""
        print("DEBUG: _show_settings called")
        try:
            show_settings_dialog(self._save_settings, self.config)
            print("DEBUG: dialog shown")
        except Exception as e:
            print(f"DEBUG: Error showing dialog: {e}")
            import traceback
            traceback.print_exc()

    def _save_settings(self, api_key: str, model: str, base_url: Optional[str], auto_start: bool):
        """Save the settings."""
        if api_key:
            self.config.set_api_key(api_key)
            self.service_provider.update_api_key()

        self.config.model = model
        self.config.base_url = base_url
        self.service_provider.update_model()

        if auto_start != self.config.auto_start:
            self.config.set_auto_start(auto_start)

    def _show_about(self):
        """Show the about dialog."""
        show_about_dialog()

    def _quit(self):
        """Quit the application."""
        AppKit.NSApp.terminate_(None)

    def run(self):
        """Run the application."""
        # Register the service
        self.service_provider.register_services()

        # Run the app
        AppHelper.runEventLoop(installInterrupt=True)
