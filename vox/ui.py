"""
Menu bar application for Vox.

Provides a menu bar icon with access to settings and configuration.
"""
import objc
import AppKit
import Foundation
from PyObjCTools import AppHelper
from typing import Optional
import time

# Import Quartz.CoreGraphics for CGEvent functions
from Quartz.CoreGraphics import (
    CGEventSourceCreate,
    CGEventCreateKeyboardEvent,
    CGEventSetFlags,
    CGEventPost,
    kCGEventSourceStateCombinedSessionState,
    kCGSessionEventTap,
    kCGEventFlagMaskCommand,
)

from vox.config import get_config
from vox.api import RewriteMode, RewriteAPI, APIKeyError, NetworkError, RateLimitError, RewriteError
from vox.service import ServiceProvider
from vox.notifications import ToastManager, ErrorNotifier
from vox.hotkey import (
    create_hotkey_manager,
    KEY_CODE_TO_CHAR,
    MODIFIER_SYMBOLS,
    format_hotkey_display,
    modifier_mask_to_string,
    parse_modifiers,
)


class EditableTextField(AppKit.NSTextField):
    """NSTextField subclass that supports Cmd+C/V/X/A in NSAlert modal sessions.

    NSAlert's modal run loop intercepts key equivalents before they reach the
    field editor.  This subclass catches Cmd+C/V/X/A in performKeyEquivalent_
    and forwards them via NSApp.sendAction_to_from_() so clipboard operations
    work normally.
    """

    def performKeyEquivalent_(self, event):
        flags = event.modifierFlags()
        if flags & AppKit.NSEventModifierFlagCommand:
            chars = event.charactersIgnoringModifiers()
            action_map = {
                "c": "copy:",
                "v": "paste:",
                "x": "cut:",
                "a": "selectAll:",
            }
            action_sel = action_map.get(chars)
            if action_sel:
                return AppKit.NSApp.sendAction_to_from_(action_sel, None, self)
        return objc.super(EditableTextField, self).performKeyEquivalent_(event)


class HotkeyRecorderField(AppKit.NSTextField):
    """NSTextField subclass that records a keyboard shortcut.

    When focused it shows "Press shortcut..." and waits for a modifier+key
    combination.  While the user holds modifier keys it previews them as
    symbols (e.g. "⌘⌥...").  Once a valid key is pressed it stores the
    result and displays it (e.g. "⌘⌥V").

    After recording, `modifiers_mask` and `key_char` hold the raw values and
    `get_modifiers_string()` / `get_key_string()` return config-compatible
    strings.
    """

    def initWithFrame_(self, frame):
        self = objc.super(HotkeyRecorderField, self).initWithFrame_(frame)
        if self is None:
            return None
        self._modifiers_mask = 0
        self._key_char = ""
        self._recording = False
        self._original_value = ""
        return self

    # -- public API ----------------------------------------------------------

    def set_hotkey(self, modifiers_str, key_str):
        """Initialise from config strings (e.g. "cmd+option", "v")."""
        self._modifiers_mask = parse_modifiers(modifiers_str)
        self._key_char = key_str.lower()
        self.setStringValue_(format_hotkey_display(self._modifiers_mask, self._key_char))

    def get_modifiers_string(self):
        return modifier_mask_to_string(self._modifiers_mask)

    def get_key_string(self):
        return self._key_char.lower() if self._key_char else "v"

    # -- focus / recording ---------------------------------------------------

    def becomeFirstResponder(self):
        result = objc.super(HotkeyRecorderField, self).becomeFirstResponder()
        if result:
            self._recording = True
            self._original_value = self.stringValue()
            self.setStringValue_("Press shortcut...")
        return result

    def resignFirstResponder(self):
        if self._recording:
            self._recording = False
            # If no valid shortcut was recorded, revert
            if not self._key_char:
                self.setStringValue_(self._original_value)
            else:
                self.setStringValue_(format_hotkey_display(self._modifiers_mask, self._key_char))
        return objc.super(HotkeyRecorderField, self).resignFirstResponder()

    # -- event handling ------------------------------------------------------

    def performKeyEquivalent_(self, event):
        if not self._recording:
            return objc.super(HotkeyRecorderField, self).performKeyEquivalent_(event)
        # Intercept everything while recording
        self._process_key_event(event)
        return True

    def keyDown_(self, event):
        if not self._recording:
            objc.super(HotkeyRecorderField, self).keyDown_(event)
            return
        self._process_key_event(event)

    def flagsChanged_(self, event):
        if not self._recording:
            objc.super(HotkeyRecorderField, self).flagsChanged_(event)
            return
        flags = event.modifierFlags()
        mask = 0
        for flag, _ in MODIFIER_SYMBOLS:
            if flags & flag:
                mask |= flag
        if mask:
            symbols = "".join(sym for f, sym in MODIFIER_SYMBOLS if mask & f)
            self.setStringValue_(symbols + "...")
        else:
            self.setStringValue_("Press shortcut...")

    # -- internal ------------------------------------------------------------

    def _process_key_event(self, event):
        keycode = event.keyCode()
        char = KEY_CODE_TO_CHAR.get(keycode)
        if char is None:
            return  # ignore non-mapped keys (e.g. pure modifier press)

        flags = event.modifierFlags()
        mask = 0
        for flag, _ in MODIFIER_SYMBOLS:
            if flags & flag:
                mask |= flag

        if not mask:
            return  # require at least one modifier

        self._modifiers_mask = mask
        self._key_char = char
        self._recording = False
        self.setStringValue_(format_hotkey_display(mask, char))

        # Move focus away to signal completion
        if self.window():
            self.window().makeFirstResponder_(None)


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
    current_hotkey_enabled = config.hotkey_enabled
    current_hotkey_modifiers = config.hotkey_modifiers
    current_hotkey_key = config.hotkey_key

    # Create container for all fields
    container = AppKit.NSView.alloc().initWithFrame_(
        Foundation.NSMakeRect(0, 0, 380, 290)
    )

    y_offset = 270

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

    api_field = EditableTextField.alloc().initWithFrame_(
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

    model_field = EditableTextField.alloc().initWithFrame_(
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

    url_field = EditableTextField.alloc().initWithFrame_(
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

    y_offset -= 35

    # Separator for hot key section
    y_offset -= 10
    separator = AppKit.NSBox.alloc().initWithFrame_(Foundation.NSMakeRect(10, y_offset, 360, 1))
    separator.setBoxType_(AppKit.NSBoxSeparator)
    container.addSubview_(separator)

    y_offset -= 30

    # Hot Key section label
    hotkey_header = AppKit.NSTextField.alloc().initWithFrame_(
        Foundation.NSMakeRect(0, y_offset, 380, 20)
    )
    hotkey_header.setStringValue_("Hot Key")
    hotkey_header.setBezeled_(False)
    hotkey_header.setDrawsBackground_(False)
    hotkey_header.setEditable_(False)
    hotkey_header.setSelectable_(False)
    hotkey_header.setFont_(AppKit.NSFont.boldSystemFontOfSize_(13))
    container.addSubview_(hotkey_header)

    y_offset -= 30

    # Hot key enabled checkbox
    hotkey_enable_label = AppKit.NSTextField.alloc().initWithFrame_(
        Foundation.NSMakeRect(0, y_offset, 100, 20)
    )
    hotkey_enable_label.setStringValue_("Hot Key:")
    hotkey_enable_label.setBezeled_(False)
    hotkey_enable_label.setDrawsBackground_(False)
    hotkey_enable_label.setEditable_(False)
    hotkey_enable_label.setSelectable_(False)
    hotkey_enable_label.setAlignment_(AppKit.NSTextAlignmentRight)
    container.addSubview_(hotkey_enable_label)

    hotkey_enable_checkbox = AppKit.NSButton.alloc().initWithFrame_(
        Foundation.NSMakeRect(110, y_offset - 2, 150, 25)
    )
    hotkey_enable_checkbox.setButtonType_(AppKit.NSSwitchButton)
    hotkey_enable_checkbox.setTitle_("Enable hot key")
    hotkey_enable_checkbox.setState_(AppKit.NSControlStateValueOn if current_hotkey_enabled else AppKit.NSControlStateValueOff)
    container.addSubview_(hotkey_enable_checkbox)

    y_offset -= 35

    # Shortcut recorder
    shortcut_label = AppKit.NSTextField.alloc().initWithFrame_(
        Foundation.NSMakeRect(0, y_offset, 100, 20)
    )
    shortcut_label.setStringValue_("Shortcut:")
    shortcut_label.setBezeled_(False)
    shortcut_label.setDrawsBackground_(False)
    shortcut_label.setEditable_(False)
    shortcut_label.setSelectable_(False)
    shortcut_label.setAlignment_(AppKit.NSTextAlignmentRight)
    container.addSubview_(shortcut_label)

    hotkey_recorder = HotkeyRecorderField.alloc().initWithFrame_(
        Foundation.NSMakeRect(110, y_offset, 120, 24)
    )
    hotkey_recorder.set_hotkey(current_hotkey_modifiers, current_hotkey_key)
    hotkey_recorder.setEditable_(True)
    hotkey_recorder.setSelectable_(True)
    container.addSubview_(hotkey_recorder)

    shortcut_help = AppKit.NSTextField.alloc().initWithFrame_(
        Foundation.NSMakeRect(240, y_offset, 140, 20)
    )
    shortcut_help.setStringValue_("Click, then press keys")
    shortcut_help.setBezeled_(False)
    shortcut_help.setDrawsBackground_(False)
    shortcut_help.setEditable_(False)
    shortcut_help.setSelectable_(False)
    shortcut_help.setTextColor_(AppKit.NSColor.secondaryLabelColor())
    shortcut_help.setFont_(AppKit.NSFont.systemFontOfSize_(11))
    container.addSubview_(shortcut_help)

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
        hotkey_enabled = hotkey_enable_checkbox.state() == AppKit.NSControlStateValueOn
        hotkey_modifiers = hotkey_recorder.get_modifiers_string()
        hotkey_key = hotkey_recorder.get_key_string()

        if callback:
            callback(api_key, model, base_url, auto_start, hotkey_enabled, hotkey_modifiers, hotkey_key)


def show_about_dialog(hotkey_modifiers: str = "option", hotkey_key: str = "v"):
    """Show about dialog."""
    # Format hot key for display using symbols
    mod_mask = parse_modifiers(hotkey_modifiers)
    hotkey_display = format_hotkey_display(mod_mask, hotkey_key)
    alert = AppKit.NSAlert.alloc().init()
    alert.setMessageText_("Vox")
    alert.setInformativeText_(
        "AI-powered text rewriting through macOS contextual menu.\n\n"
        "Version 0.1.0\n\n"
        f"Right-click any text to rewrite with AI.\n"
        f"Press {hotkey_display} with selected text for quick access."
    )
    alert.setAlertStyle_(AppKit.NSAlertStyleInformational)
    alert.addButtonWithTitle_("OK")
    AppKit.NSApp.activateIgnoringOtherApps_(True)
    alert.runModal()


class ModePickerDialog(AppKit.NSObject):
    """Dialog for selecting a rewrite mode when triggered via hot key."""

    def init(self):
        """Initialize the mode picker."""
        self = objc.super(ModePickerDialog, self).init()
        if self is None:
            return None
        self._callback = None
        self._selected_mode = None
        self._frontmost_app = None  # Store the frontmost app before showing dialog
        return self

    def show_mode_picker(self, callback):
        """
        Show a mode picker dialog.

        Args:
            callback: Function to call with selected RewriteMode.

        Returns:
            The frontmost app (NSRunningApplication) before the dialog was shown,
            or None if it couldn't be determined.
        """
        # Clear any previous callback to prevent memory leaks
        self._callback = None
        self._callback = callback
        self._selected_mode = None

        # Save the current frontmost application before showing dialog
        workspace = AppKit.NSWorkspace.sharedWorkspace()
        self._frontmost_app = workspace.frontmostApplication()

        alert = AppKit.NSAlert.alloc().init()
        alert.setMessageText_("Rewrite with Vox")
        alert.setInformativeText_("Choose a rewrite style:")
        alert.setAlertStyle_(AppKit.NSAlertStyleInformational)

        # Add buttons for each mode
        for mode, display_name in RewriteAPI.get_all_modes():
            alert.addButtonWithTitle_(display_name)

        # Add cancel button
        alert.addButtonWithTitle_("Cancel")

        # Activate app and show modal
        AppKit.NSApp.activateIgnoringOtherApps_(True)
        response = alert.runModal()

        # Explicitly dismiss the alert window and drain pending UI events
        # so it is visually gone before the callback blocks on the API call.
        alert.window().orderOut_(None)
        while True:
            event = AppKit.NSApp.nextEventMatchingMask_untilDate_inMode_dequeue_(
                AppKit.NSEventMaskAny,
                Foundation.NSDate.distantPast(),
                AppKit.NSDefaultRunLoopMode,
                True,
            )
            if event is None:
                break
            AppKit.NSApp.sendEvent_(event)

        # Map button response to mode
        # NSAlert returns NSAlertFirstButtonReturn (1000) for first button, 1001 for second, etc.
        button_index = response - AppKit.NSAlertFirstButtonReturn
        modes = list(RewriteMode)
        if 0 <= button_index < len(modes):
            self._selected_mode = modes[button_index]
            if self._callback:
                # Clear callback before calling to prevent memory leaks
                cb = self._callback
                self._callback = None
                cb(self._selected_mode)
        else:
            # Clear callback on cancel
            self._callback = None

        return self._frontmost_app


def get_selected_text() -> Optional[str]:
    """
    Get the currently selected text by simulating Cmd+C.

    Returns:
        The selected text, or None if no text was selected.
    """
    try:
        # Save current clipboard content
        pasteboard = AppKit.NSPasteboard.generalPasteboard()
        saved_content = pasteboard.stringForType_(AppKit.NSPasteboardTypeString)

        # Simulate Cmd+C to copy selected text
        # We use CGEvent to simulate keypresses
        source = CGEventSourceCreate(kCGEventSourceStateCombinedSessionState)

        # Press Cmd
        cmd_down = CGEventCreateKeyboardEvent(
            source, 0x37, True  # 0x37 is Cmd key
        )
        # Press C
        c_down = CGEventCreateKeyboardEvent(
            source, 0x08, True  # 0x08 is C key
        )
        # Release C
        c_up = CGEventCreateKeyboardEvent(
            source, 0x08, False
        )
        # Release Cmd
        cmd_up = CGEventCreateKeyboardEvent(
            source, 0x37, False
        )

        # Set flags to include Cmd
        cmd_flags = kCGEventFlagMaskCommand
        CGEventSetFlags(c_down, cmd_flags)
        CGEventSetFlags(c_up, cmd_flags)

        # Send events
        CGEventPost(kCGSessionEventTap, cmd_down)
        time.sleep(0.01)
        CGEventPost(kCGSessionEventTap, c_down)
        time.sleep(0.01)
        CGEventPost(kCGSessionEventTap, c_up)
        time.sleep(0.01)
        CGEventPost(kCGSessionEventTap, cmd_up)

        # Wait a bit for the copy to complete
        time.sleep(0.05)

        # Get the copied text
        selected_text = pasteboard.stringForType_(AppKit.NSPasteboardTypeString)

        # Restore previous clipboard content
        if saved_content:
            pasteboard.clearContents()
            pasteboard.setString_forType_(saved_content, AppKit.NSPasteboardTypeString)

        return selected_text

    except Exception as e:
        print(f"Error getting selected text: {e}")
        import traceback
        traceback.print_exc()
        return None


def paste_text(text: str):
    """
    Paste text to the current application by simulating Cmd+V.

    Args:
        text: The text to paste.
    """
    try:
        # Set clipboard content
        pasteboard = AppKit.NSPasteboard.generalPasteboard()
        pasteboard.clearContents()
        pasteboard.setString_forType_(text, AppKit.NSPasteboardTypeString)

        # Simulate Cmd+V to paste
        source = CGEventSourceCreate(kCGEventSourceStateCombinedSessionState)

        # Press Cmd
        cmd_down = CGEventCreateKeyboardEvent(
            source, 0x37, True
        )
        # Press V
        v_down = CGEventCreateKeyboardEvent(
            source, 0x09, True  # 0x09 is V key
        )
        # Release V
        v_up = CGEventCreateKeyboardEvent(
            source, 0x09, False
        )
        # Release Cmd
        cmd_up = CGEventCreateKeyboardEvent(
            source, 0x37, False
        )

        # Set flags to include Cmd
        cmd_flags = kCGEventFlagMaskCommand
        CGEventSetFlags(v_down, cmd_flags)
        CGEventSetFlags(v_up, cmd_flags)

        # Send events
        CGEventPost(kCGSessionEventTap, cmd_down)
        time.sleep(0.01)
        CGEventPost(kCGSessionEventTap, v_down)
        time.sleep(0.01)
        CGEventPost(kCGSessionEventTap, v_up)
        time.sleep(0.01)
        CGEventPost(kCGSessionEventTap, cmd_up)

    except Exception as e:
        print(f"Error pasting text: {e}")
        import traceback
        traceback.print_exc()


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

        # Create toast manager for notifications
        self._toast_manager = ToastManager()

        # Create mode picker dialog
        self._mode_picker = ModePickerDialog.alloc().init()

        # Create hot key manager
        self._hotkey_manager = create_hotkey_manager()
        self._hotkey_manager.set_callback(self._handle_hotkey)
        self._hotkey_manager.set_enabled(self.config.hotkey_enabled)
        self._hotkey_manager.set_hotkey(self.config.hotkey_modifiers, self.config.hotkey_key)

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

    def _save_settings(self, api_key: str, model: str, base_url: Optional[str], auto_start: bool,
                      hotkey_enabled: bool, hotkey_modifiers: str, hotkey_key: str):
        """Save the settings."""
        if api_key:
            self.config.set_api_key(api_key)
            self.service_provider.update_api_key()

        self.config.model = model
        self.config.base_url = base_url
        self.service_provider.update_model()

        if auto_start != self.config.auto_start:
            self.config.set_auto_start(auto_start)

        # Update hot key settings
        self.config.hotkey_enabled = hotkey_enabled
        self.config.hotkey_modifiers = hotkey_modifiers
        self.config.hotkey_key = hotkey_key

        # Re-register hot key with new settings
        self._hotkey_manager.set_enabled(hotkey_enabled)
        self._hotkey_manager.set_hotkey(hotkey_modifiers, hotkey_key)
        if hotkey_enabled:
            self._hotkey_manager.reregister_hotkey()

    def _show_about(self):
        """Show the about dialog."""
        show_about_dialog(self.config.hotkey_modifiers, self.config.hotkey_key)

    def _quit(self):
        """Quit the application."""
        AppKit.NSApp.terminate_(None)

    def _handle_hotkey(self):
        """Handle the hot key trigger."""
        print("Hot key triggered!")

        try:
            # Check if API key is configured
            api_key = self.config.get_api_key()
            if not api_key:
                ErrorNotifier.show_api_key_error()
                return

            # Get selected text
            text = get_selected_text()
            if not text or not text.strip():
                print("No text selected")
                return

            print(f"Selected text: {text!r}")

            # Store the text for use after mode selection
            # (selection might be lost after mode picker dialog closes)
            self._pending_rewrite_text = text

            # Show mode picker dialog and capture the frontmost app
            self._frontmost_app_before_picker = self._mode_picker.show_mode_picker(self._process_text_with_mode)

        except Exception as e:
            print(f"Error handling hot key: {e}")
            import traceback
            traceback.print_exc()

    def _process_text_with_mode(self, mode: RewriteMode):
        """
        Process the text with the selected mode.

        Args:
            mode: The rewrite mode to use.
        """
        if mode is None:
            print("Mode selection cancelled")
            return

        try:
            # Get API client
            api_key = self.config.get_api_key()
            if not api_key:
                ErrorNotifier.show_api_key_error()
                return

            api_client = RewriteAPI(api_key, self.config.model, self.config.base_url)

            # Use the stored text from when the hotkey was pressed
            # (selection is likely gone after mode picker dialog)
            text = getattr(self, '_pending_rewrite_text', None)
            if not text:
                print("No text to rewrite")
                return

            # Show loading toast
            mode_name = RewriteAPI.get_display_name(mode)
            self._toast_manager.show(f"{mode_name} with Vox...")

            # Allow the toast to render before blocking on API call
            AppKit.NSApp.currentEvent()  # Process any pending events
            time.sleep(0.01)  # Small delay to ensure UI updates

            # Process the text
            result = api_client.rewrite(text, mode)
            print(f"Rewritten text: {result!r}")

            # First, put the result in the clipboard (so manual paste works)
            pasteboard = AppKit.NSPasteboard.generalPasteboard()
            pasteboard.clearContents()
            pasteboard.setString_forType_(result, AppKit.NSPasteboardTypeString)

            # Try to restore focus to the previous app and paste
            frontmost_app = getattr(self, '_frontmost_app_before_picker', None)
            if frontmost_app and not frontmost_app.isTerminated():
                # Activate the previous app
                success = frontmost_app.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)

                # Wait for the app to actually become frontmost before pasting
                if success:
                    workspace = AppKit.NSWorkspace.sharedWorkspace()
                    for _ in range(20):  # Max 1 second (20 * 0.05s)
                        current_frontmost = workspace.frontmostApplication()
                        if (current_frontmost and
                            current_frontmost.processIdentifier() == frontmost_app.processIdentifier()):
                            break
                        time.sleep(0.05)

            # Now paste the text
            paste_text(result)

            # Clear stored text
            self._pending_rewrite_text = None

            # Hide toast
            self._toast_manager.hide()

        except (APIKeyError, NetworkError, RateLimitError, RewriteError) as e:
            ErrorNotifier.show_generic_error(str(e))
            self._toast_manager.hide()
            self._pending_rewrite_text = None

        except Exception as e:
            print(f"Error processing text: {e}")
            import traceback
            traceback.print_exc()
            ErrorNotifier.show_generic_error(f"Error: {e}")
            self._toast_manager.hide()
            self._pending_rewrite_text = None

    def run(self):
        """Run the application."""
        # Register the service
        self.service_provider.register_services()

        # Register the hot key
        self._hotkey_manager.register_hotkey()

        # Run the app
        AppHelper.runEventLoop(installInterrupt=True)
