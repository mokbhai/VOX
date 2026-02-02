"""
Notification system for Vox.

Provides toast popups near the cursor for loading state
and macOS notification banners for errors.
"""
import objc
import AppKit
import Foundation
from PyObjCTools import AppHelper
from typing import Optional


class ToastWindow(AppKit.NSWindow):
    """A small toast popup window that appears near the cursor."""

    _instance = None
    _text_field = objc.ivar()

    @classmethod
    def create(cls):
        """Create and initialize the toast window."""
        frame = Foundation.NSMakeRect(0, 0, 200, 50)
        window = cls.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            AppKit.NSWindowStyleMaskBorderless,
            AppKit.NSBackingStoreBuffered,
            False,
        )
        if window is None:
            return None

        # Configure appearance
        window.setTitle_("Vox")
        window.setOpaque_(False)
        window.setBackgroundColor_(AppKit.NSColor.colorWithDeviceWhite_alpha_(0.2, 0.9))
        window.setLevel_(AppKit.NSFloatingWindowLevel)

        # Create text field
        text_frame = Foundation.NSMakeRect(10, 10, 180, 30)
        window._text_field = AppKit.NSTextField.alloc().initWithFrame_(text_frame)
        window._text_field.setStringValue_("Rewriting with Vox...")
        window._text_field.setBezeled_(False)
        window._text_field.setDrawsBackground_(False)
        window._text_field.setEditable_(False)
        window._text_field.setSelectable_(False)
        window._text_field.setTextColor_(AppKit.NSColor.whiteColor())
        window._text_field.setAlignment_(AppKit.NSTextAlignmentCenter)
        window._text_field.setFont_(AppKit.NSFont.systemFontOfSize_(13))

        # Add text field to window
        content = AppKit.NSView.alloc().initWithFrame_(frame)
        window.setContentView_(content)
        window.contentView().addSubview_(window._text_field)

        # Round corners
        window.contentView().setWantsLayer_(True)
        layer = window.contentView().layer()
        if layer:
            layer.setCornerRadius_(10)

        return window

    def show_at_cursor(self):
        """Show the toast window near the mouse cursor."""
        mouse_location = AppKit.NSEvent.mouseLocation()
        window_height = self.frame().size.height

        x = mouse_location.x + 15
        y = mouse_location.y - window_height - 15

        self.setFrameTopLeftPoint_(Foundation.NSMakePoint(x, y))
        self.makeKeyAndOrderFront_(None)
        self.orderFrontRegardless()

    def hide(self):
        """Hide the toast window."""
        self.orderOut_(None)

    @classmethod
    def get_instance(cls):
        """Get the singleton toast window instance."""
        if cls._instance is None:
            cls._instance = cls.create()
        return cls._instance


class ErrorNotifier:
    """Handles error notifications via macOS Notification Center."""

    @staticmethod
    def show_error(title: str, message: str):
        """
        Show an error notification.

        Args:
            title: The notification title.
            message: The error message.
        """
        # Create a user notification
        notification = AppKit.NSUserNotification.alloc().init()
        notification.setTitle_(title)
        notification.setInformativeText_(message)
        notification.setSoundName_(AppKit.NSUserNotificationDefaultSoundName)

        # Deliver the notification
        center = AppKit.NSUserNotificationCenter.defaultUserNotificationCenter()
        center.deliverNotification_(notification)

    @staticmethod
    def show_api_key_error():
        """Show notification for missing API key."""
        ErrorNotifier.show_error(
            "Vox - API Key Required",
            "Please set your OpenAI API key in Vox settings"
        )

    @staticmethod
    def show_network_error():
        """Show notification for network error."""
        ErrorNotifier.show_error(
            "Vox - Network Error",
            "Network error - check your connection"
        )

    @staticmethod
    def show_rate_limit_error():
        """Show notification for rate limit."""
        ErrorNotifier.show_error(
            "Vox - Rate Limit",
            "OpenAI rate limit reached - please wait"
        )

    @staticmethod
    def show_invalid_key_error():
        """Show notification for invalid API key."""
        ErrorNotifier.show_error(
            "Vox - Invalid API Key",
            "Invalid API key - check Vox settings"
        )

    @staticmethod
    def show_generic_error(error_message: str):
        """Show a generic error notification."""
        ErrorNotifier.show_error(
            "Vox Error",
            error_message
        )


class ToastManager:
    """Manages the toast popup for loading state."""

    def __init__(self):
        """Initialize the toast manager."""
        self._toast: Optional[ToastWindow] = None
        self._is_visible = False

    def show(self, message: str = "Rewriting with Vox..."):
        """
        Show the toast popup near the cursor.

        Args:
            message: The message to display.
        """
        toast = ToastWindow.get_instance()
        toast._text_field.setStringValue_(message)
        toast.show_at_cursor()
        self._is_visible = True

    def hide(self):
        """Hide the toast popup."""
        if self._is_visible:
            toast = ToastWindow.get_instance()
            toast.hide()
            self._is_visible = False

    def is_visible(self) -> bool:
        """Check if toast is currently visible."""
        return self._is_visible
