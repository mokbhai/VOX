"""
Global hot key handling for Vox using Quartz CGEventTap.

Uses CGEventTapCreate on a dedicated background thread with its own CFRunLoop,
matching the proven pattern used by pynput's macOS keyboard listener.
"""
import threading

import AppKit
import Quartz
from ApplicationServices import (
    AXIsProcessTrusted,
    AXIsProcessTrustedWithOptions,
    kAXTrustedCheckOptionPrompt,
)


# CGEvent modifier flag constants
kCGEventFlagMaskCommand = Quartz.kCGEventFlagMaskCommand
kCGEventFlagMaskAlternate = Quartz.kCGEventFlagMaskAlternate
kCGEventFlagMaskControl = Quartz.kCGEventFlagMaskControl
kCGEventFlagMaskShift = Quartz.kCGEventFlagMaskShift
kCGEventKeyDown = Quartz.kCGEventKeyDown
kCGEventTapDisabledByTimeout = Quartz.kCGEventTapDisabledByTimeout
kCGEventTapDisabledByUserInput = Quartz.kCGEventTapDisabledByUserInput
kCGKeyboardEventKeycode = Quartz.kCGKeyboardEventKeycode
kCGKeyboardEventAutorepeat = Quartz.kCGKeyboardEventAutorepeat


def has_accessibility_permission() -> bool:
    """Check if Accessibility permission is granted."""
    try:
        return AXIsProcessTrusted()
    except Exception as e:
        print(f"Error checking accessibility permission: {e}")
        return False


def request_accessibility_permission() -> bool:
    """
    Request Accessibility permission from the user.

    Shows the system permission dialog if not already granted.
    """
    try:
        options = {kAXTrustedCheckOptionPrompt: True}
        return AXIsProcessTrustedWithOptions(options)
    except Exception as e:
        print(f"Error requesting accessibility permission: {e}")
        return False


# Key code mapping for common keys
KEY_CODES = {
    'a': 0x00, 'b': 0x0B, 'c': 0x08, 'd': 0x02, 'e': 0x0E,
    'f': 0x03, 'g': 0x05, 'h': 0x04, 'i': 0x22, 'j': 0x26,
    'k': 0x28, 'l': 0x25, 'm': 0x2E, 'n': 0x2D, 'o': 0x1F,
    'p': 0x23, 'q': 0x0C, 'r': 0x0F, 's': 0x01, 't': 0x11,
    'u': 0x20, 'v': 0x09, 'w': 0x0D, 'x': 0x07, 'y': 0x10,
    'z': 0x06,
    '0': 0x1D, '1': 0x12, '2': 0x13, '3': 0x14, '4': 0x15,
    '5': 0x17, '6': 0x16, '7': 0x1A, '8': 0x1C, '9': 0x19,
}

# Modifier flag constants (CGEvent values)
MODIFIER_FLAGS = {
    'cmd': kCGEventFlagMaskCommand,
    'command': kCGEventFlagMaskCommand,
    'option': kCGEventFlagMaskAlternate,
    'opt': kCGEventFlagMaskAlternate,
    'alt': kCGEventFlagMaskAlternate,
    'control': kCGEventFlagMaskControl,
    'ctrl': kCGEventFlagMaskControl,
    'shift': kCGEventFlagMaskShift,
}

# Mask covering all four modifier bits we check
ALL_MODIFIER_FLAGS_MASK = (
    kCGEventFlagMaskCommand
    | kCGEventFlagMaskAlternate
    | kCGEventFlagMaskControl
    | kCGEventFlagMaskShift
)


def get_key_code(key_str: str) -> int:
    """Get key code for a key character."""
    key = key_str.lower()
    if len(key) == 0:
        return 0x09  # Default to V
    return KEY_CODES.get(key[0], 0x09)


def parse_modifiers(modifiers_str: str) -> int:
    """Parse modifier string to CGEvent flag mask."""
    mask = 0
    parts = modifiers_str.lower().replace(' ', '+').split('+')
    for part in parts:
        mask |= MODIFIER_FLAGS.get(part, 0)
    return mask


class HotKeyManager:
    """
    Manages global hot key using Quartz CGEventTap.

    The event tap runs on a dedicated background thread with its own CFRunLoop,
    matching the pattern used by pynput's proven macOS keyboard listener.
    """

    def __init__(self):
        """Initialize the hot key manager."""
        self._callback = None
        self._enabled = True
        self._modifiers_str = "option"
        self._key_str = "v"
        self._target_key_code = 0
        self._target_modifiers = 0
        self._is_registered = False
        # CGEventTap state
        self._tap = None
        self._tap_callback = None
        self._run_loop_source = None
        self._run_loop = None
        self._tap_thread = None

    def set_callback(self, callback):
        """Set the callback function."""
        self._callback = callback

    def set_hotkey(self, modifiers: str, key: str):
        """Set the hot key combination."""
        self._modifiers_str = modifiers
        self._key_str = key

    def set_enabled(self, enabled: bool):
        """Enable or disable the hot key."""
        self._enabled = enabled
        if not enabled and self._is_registered:
            self.unregister_hotkey()

    def register_hotkey(self) -> bool:
        """Register the global hot key using CGEventTap."""
        if not self._enabled:
            return False

        if self._is_registered:
            return True

        print(f"Accessibility permission: {has_accessibility_permission()}", flush=True)

        if not has_accessibility_permission():
            print("Requesting Accessibility permission...")
            request_accessibility_permission()
            if not has_accessibility_permission():
                self._show_accessibility_dialog()
                return False

        try:
            self._target_key_code = get_key_code(self._key_str)
            self._target_modifiers = parse_modifiers(self._modifiers_str)

            print(
                f"Setting up CGEventTap hot key: {self._modifiers_str}+{self._key_str} "
                f"(key={self._target_key_code}, mod={self._target_modifiers})",
                flush=True,
            )

            # Build the callback — capture self directly (prevented from GC
            # by storing in self._tap_callback)
            def tap_callback(proxy, event_type, event, user_info):
                return self._handle_cg_event(proxy, event_type, event)

            self._tap_callback = tap_callback

            # Event mask: key down + modifier changes
            event_mask = (
                Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
                | Quartz.CGEventMaskBit(Quartz.kCGEventKeyUp)
                | Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged)
            )

            # Create the event tap — using Quartz module directly (proven pattern)
            tap = Quartz.CGEventTapCreate(
                Quartz.kCGSessionEventTap,
                Quartz.kCGHeadInsertEventTap,
                Quartz.kCGEventTapOptionListenOnly,
                event_mask,
                tap_callback,
                None,
            )

            if tap is None:
                print(
                    "CGEventTapCreate returned None — Accessibility is granted, "
                    "likely missing Input Monitoring permission.",
                    flush=True,
                )
                self._show_input_monitoring_dialog()
                return False

            self._tap = tap

            # Create run loop source — use None for default allocator (pynput pattern)
            self._run_loop_source = Quartz.CFMachPortCreateRunLoopSource(
                None, tap, 0
            )

            # Start background thread with its own CFRunLoop (pynput pattern)
            self._tap_thread = threading.Thread(
                target=self._run_tap_loop,
                name="VoxHotkeyTap",
                daemon=True,
            )
            self._tap_thread.start()

            self._is_registered = True
            print(f"Hot key registered: {self._modifiers_str}+{self._key_str}", flush=True)
            return True

        except Exception as e:
            print(f"Error registering hot key: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _run_tap_loop(self):
        """Background thread running its own CFRunLoop for the event tap."""
        self._run_loop = Quartz.CFRunLoopGetCurrent()
        Quartz.CFRunLoopAddSource(
            self._run_loop,
            self._run_loop_source,
            Quartz.kCFRunLoopDefaultMode,
        )
        Quartz.CGEventTapEnable(self._tap, True)
        print("CGEventTap run loop started on background thread", flush=True)
        Quartz.CFRunLoopRun()
        print("CGEventTap run loop exited", flush=True)

    def _handle_cg_event(self, proxy, event_type, event):
        """Handle a CGEvent from the tap callback (runs on background thread)."""
        try:
            if event_type == kCGEventTapDisabledByTimeout:
                print("CGEventTap disabled by timeout — re-enabling", flush=True)
                Quartz.CGEventTapEnable(self._tap, True)
                return event

            if event_type == kCGEventTapDisabledByUserInput:
                return event

            if event_type != Quartz.kCGEventKeyDown:
                return event

            keycode = Quartz.CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            if keycode != self._target_key_code:
                return event

            # Skip key-repeat events
            autorepeat = Quartz.CGEventGetIntegerValueField(event, kCGKeyboardEventAutorepeat)
            if autorepeat:
                return event

            # Check modifier flags — only compare the four standard modifiers
            flags = Quartz.CGEventGetFlags(event)
            relevant_flags = flags & ALL_MODIFIER_FLAGS_MASK
            if relevant_flags != self._target_modifiers:
                return event

            # Hot key matched — dispatch callback to the main thread
            if self._enabled and self._callback:
                print(f"Hot key triggered: {self._modifiers_str}+{self._key_str}", flush=True)
                AppKit.NSOperationQueue.mainQueue().addOperationWithBlock_(self._callback)

            return event

        except Exception as e:
            print(f"Error in CGEventTap callback: {e}")
            import traceback
            traceback.print_exc()
            return event

    def unregister_hotkey(self):
        """Unregister the hot key."""
        if not self._is_registered:
            return

        try:
            if self._tap:
                Quartz.CGEventTapEnable(self._tap, False)

            if self._run_loop:
                Quartz.CFRunLoopStop(self._run_loop)

            if self._tap_thread:
                self._tap_thread.join(timeout=2.0)

            self._tap = None
            self._tap_callback = None
            self._run_loop_source = None
            self._run_loop = None
            self._tap_thread = None
            self._is_registered = False
            print("Hot key unregistered")

        except Exception as e:
            print(f"Error unregistering hot key: {e}")

    def reregister_hotkey(self):
        """Re-register the hot key."""
        self.unregister_hotkey()
        return self.register_hotkey()

    def _show_accessibility_dialog(self):
        """Show dialog for Accessibility and Input Monitoring permissions."""
        alert = AppKit.NSAlert.alloc().init()
        alert.setMessageText_("Permissions Required")
        alert.setInformativeText_(
            "Vox needs two permissions to use global hot keys:\n\n"
            "1. Open System Settings → Privacy & Security\n"
            "2. Enable Accessibility for Vox (or Terminal in dev mode)\n"
            "3. Enable Input Monitoring for Vox (or Terminal in dev mode)\n\n"
            "Then restart Vox."
        )
        alert.setAlertStyle_(AppKit.NSAlertStyleWarning)
        alert.addButtonWithTitle_("Open Accessibility")
        alert.addButtonWithTitle_("Open Input Monitoring")
        alert.addButtonWithTitle_("Cancel")

        AppKit.NSApp.activateIgnoringOtherApps_(True)

        response = alert.runModal()

        if response == AppKit.NSAlertFirstButtonReturn:
            AppKit.NSWorkspace.sharedWorkspace().openURL_(
                AppKit.NSURL.URLWithString_(
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
                )
            )
        elif response == AppKit.NSAlertSecondButtonReturn:
            AppKit.NSWorkspace.sharedWorkspace().openURL_(
                AppKit.NSURL.URLWithString_(
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"
                )
            )

    def _show_input_monitoring_dialog(self):
        """Show dialog for Input Monitoring permission."""
        alert = AppKit.NSAlert.alloc().init()
        alert.setMessageText_("Input Monitoring Permission Required")
        alert.setInformativeText_(
            "Vox needs Input Monitoring permission to detect global hot keys.\n\n"
            "1. Open System Settings\n"
            "2. Go to Privacy & Security → Input Monitoring\n"
            "3. Find Terminal or Vox and enable it\n\n"
            "Then restart Vox."
        )
        alert.setAlertStyle_(AppKit.NSAlertStyleWarning)
        alert.addButtonWithTitle_("Open System Settings")
        alert.addButtonWithTitle_("Cancel")

        AppKit.NSApp.activateIgnoringOtherApps_(True)

        response = alert.runModal()

        if response == AppKit.NSAlertFirstButtonReturn:
            AppKit.NSWorkspace.sharedWorkspace().openURL_(
                AppKit.NSURL.URLWithString_(
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"
                )
            )


def create_hotkey_manager():
    """Factory function to create a hot key manager instance."""
    return HotKeyManager()
