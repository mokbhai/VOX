"""
macOS Services API integration for Vox.

Handles text processing requests from the contextual menu
using the NSServices mechanism via PyObjC.
"""
import AppKit
import Foundation
from PyObjCTools import AppHelper
from typing import Optional

from vox.config import get_config
from vox.api import RewriteAPI, RewriteMode, RewriteError, APIKeyError, NetworkError, RateLimitError
from vox.notifications import ToastManager, ErrorNotifier


class ServiceProvider(AppKit.NSObject):
    """
    Service provider for macOS NSServices integration.

    This class receives text from the contextual menu and processes it
    using the OpenAI API, then writes the transformed text back.
    """

    def init(self):
        """Initialize the service provider."""
        self = objc.super(ServiceProvider, self).init()
        if self is None:
            return None

        self._toast_manager = ToastManager()
        self._api_client: Optional[RewriteAPI] = None
        self._current_mode = RewriteMode.FIX_GRAMMAR  # Default mode
        return self

    def _get_api_client(self) -> Optional[RewriteAPI]:
        """
        Get or create the API client.

        Returns:
            RewriteAPI instance if API key is configured, None otherwise.
        """
        if self._api_client is None:
            config = get_config()
            api_key = config.get_api_key()
            if not api_key:
                return None
            self._api_client = RewriteAPI(api_key, config.model, config.base_url)
        return self._api_client

    def _reset_api_client(self):
        """Reset the API client (e.g., when API key changes)."""
        self._api_client = None

    # Service methods - these are called by macOS when the service is invoked

    def fixGrammarService_userData_error_(self, pasteboard: AppKit.NSPasteboard, userData: str, error: list) -> bool:
        """
        Handle the 'Fix Grammar' service invocation.

        Args:
            pasteboard: The pasteboard containing the selected text.
            userData: Additional data (unused).
            error: Error list to populate if an error occurs.

        Returns:
            True if successful, False otherwise.
        """
        return self._handle_service(pasteboard, RewriteMode.FIX_GRAMMAR, error)

    def professionalService_userData_error_(self, pasteboard: AppKit.NSPasteboard, userData: str, error: list) -> bool:
        """Handle the 'Professional' service invocation."""
        return self._handle_service(pasteboard, RewriteMode.PROFESSIONAL, error)

    def conciseService_userData_error_(self, pasteboard: AppKit.NSPasteboard, userData: str, error: list) -> bool:
        """Handle the 'Concise' service invocation."""
        return self._handle_service(pasteboard, RewriteMode.CONCISE, error)

    def friendlyService_userData_error_(self, pasteboard: AppKit.NSPasteboard, userData: str, error: list) -> bool:
        """Handle the 'Friendly' service invocation."""
        return self._handle_service(pasteboard, RewriteMode.FRIENDLY, error)

    def _handle_service(self, pasteboard: AppKit.NSPasteboard, mode: RewriteMode, error: list) -> bool:
        """
        Handle a service invocation for any mode.

        Args:
            pasteboard: The pasteboard containing the selected text.
            mode: The rewrite mode to apply.
            error: Error list to populate if an error occurs.

        Returns:
            True if successful, False otherwise.
        """
        # Get API client
        api_client = self._get_api_client()
        if api_client is None:
            ErrorNotifier.show_api_key_error()
            error.append(AppKit.NS_ERROR_NOT_SUPPORTED)
            return False

        # Read text from pasteboard
        text = self._read_text_from_pasteboard(pasteboard)
        if not text:
            error.append(AppKit.NS_ERROR_NOT_SUPPORTED)
            return False

        # Show loading toast
        mode_name = RewriteAPI.get_display_name(mode)
        self._toast_manager.show(f"{mode_name} with Vox...")

        try:
            # Process the text
            result = api_client.rewrite(text, mode)

            # Write result back to pasteboard
            self._write_text_to_pasteboard(pasteboard, result)

            # Hide toast
            self._toast_manager.hide()
            return True

        except APIKeyError:
            ErrorNotifier.show_invalid_key_error()
            self._toast_manager.hide()
            error.append(AppKit.NS_ERROR_NOT_SUPPORTED)
            return False

        except NetworkError:
            ErrorNotifier.show_network_error()
            self._toast_manager.hide()
            error.append(AppKit.NS_ERROR_NOT_SUPPORTED)
            return False

        except RateLimitError:
            ErrorNotifier.show_rate_limit_error()
            self._toast_manager.hide()
            error.append(AppKit.NS_ERROR_NOT_SUPPORTED)
            return False

        except RewriteError as e:
            ErrorNotifier.show_generic_error(str(e))
            self._toast_manager.hide()
            error.append(AppKit.NS_ERROR_NOT_SUPPORTED)
            return False

        except Exception as e:
            ErrorNotifier.show_generic_error(f"Unexpected error: {e}")
            self._toast_manager.hide()
            error.append(AppKit.NS_ERROR_NOT_SUPPORTED)
            return False

    def _read_text_from_pasteboard(self, pasteboard: AppKit.NSPasteboard) -> Optional[str]:
        """
        Read text string from the pasteboard.

        Args:
            pasteboard: The pasteboard to read from.

        Returns:
            The text string if found, None otherwise.
        """
        # Get pasteboard types
        types = pasteboard.types()

        # Check for string type
        if AppKit.NSStringPboardType in types:
            return pasteboard.stringForType_(AppKit.NSStringPboardType)

        return None

    def _write_text_to_pasteboard(self, pasteboard: AppKit.NSPasteboard, text: str):
        """
        Write text string to the pasteboard.

        Args:
            pasteboard: The pasteboard to write to.
            text: The text to write.
        """
        # Clear the pasteboard and declare new types
        pasteboard.clearContents()
        pasteboard.declareTypes_owner_([AppKit.NSStringPboardType], None)

        # Write the text
        pasteboard.setString_forType_(text, AppKit.NSStringPboardType)

    def register_services(self):
        """Register the services with macOS."""
        # Register the service provider with Distributed Objects (DO)
        # The port name must match NSPortName in Info.plist
        connection = Foundation.NSConnection.defaultConnection()
        connection.setRootObject_(self)
        registered = connection.registerName_("Vox")

        import sys
        print(f"DEBUG: NSConnection registered='Vox': {registered}", flush=True)
        print(f"DEBUG: Connection root object: {connection.rootObject()}", flush=True)

        # Trigger a refresh of services via subprocess
        import subprocess
        try:
            result = subprocess.run(["/System/Library/CoreServices/pbs", "-flush"],
                         check=False, capture_output=True, text=True)
            print(f"DEBUG: pbs -flush output: {result.stderr}", flush=True)
        except FileNotFoundError:
            pass  # pbs command not available

    def update_api_key(self):
        """Update the API client when the API key changes."""
        self._reset_api_client()

    def update_model(self):
        """Update the API client when the model changes."""
        self._reset_api_client()


import objc
