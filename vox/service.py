"""
macOS Services API integration for Vox.

Handles text processing requests from the contextual menu
using the NSServices mechanism via PyObjC.
"""
import sys
import objc
import AppKit
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
    # Signature: (void)name:(NSPasteboard*)pboard userData:(NSString*)userData error:(NSString**)error

    @objc.typedSelector(b"v@:@@o^@")
    def fixGrammarService_userData_error_(self, pasteboard, userData, error):
        print("SERVICE CALLED: fixGrammarService", flush=True)
        self._handle_service(pasteboard, RewriteMode.FIX_GRAMMAR)

    @objc.typedSelector(b"v@:@@o^@")
    def professionalService_userData_error_(self, pasteboard, userData, error):
        print("SERVICE CALLED: professionalService", flush=True)
        self._handle_service(pasteboard, RewriteMode.PROFESSIONAL)

    @objc.typedSelector(b"v@:@@o^@")
    def conciseService_userData_error_(self, pasteboard, userData, error):
        print("SERVICE CALLED: conciseService", flush=True)
        self._handle_service(pasteboard, RewriteMode.CONCISE)

    @objc.typedSelector(b"v@:@@o^@")
    def friendlyService_userData_error_(self, pasteboard, userData, error):
        print("SERVICE CALLED: friendlyService", flush=True)
        self._handle_service(pasteboard, RewriteMode.FRIENDLY)

    def _handle_service(self, pasteboard, mode):
        """Handle a service invocation for any mode."""
        print(f"DEBUG _handle_service: mode={mode}", flush=True)
        try:
            # Get API client
            api_client = self._get_api_client()
            print(f"DEBUG: api_client={api_client}", flush=True)
            if api_client is None:
                ErrorNotifier.show_api_key_error()
                return

            # Read text from pasteboard
            text = self._read_text_from_pasteboard(pasteboard)
            print(f"DEBUG: text={text!r}", flush=True)
            if not text:
                return

            # Show loading toast
            mode_name = RewriteAPI.get_display_name(mode)
            self._toast_manager.show(f"{mode_name} with Vox...")

            # Process the text
            print("DEBUG: calling API...", flush=True)
            result = api_client.rewrite(text, mode)
            print(f"DEBUG: API result={result!r}", flush=True)

            # Write result back to pasteboard
            self._write_text_to_pasteboard(pasteboard, result)
            print("DEBUG: wrote to pasteboard, done!", flush=True)

            # Hide toast
            self._toast_manager.hide()

        except APIKeyError:
            ErrorNotifier.show_invalid_key_error()
            self._toast_manager.hide()

        except NetworkError:
            ErrorNotifier.show_network_error()
            self._toast_manager.hide()

        except RateLimitError:
            ErrorNotifier.show_rate_limit_error()
            self._toast_manager.hide()

        except RewriteError as e:
            ErrorNotifier.show_generic_error(str(e))
            self._toast_manager.hide()

        except Exception as e:
            print(f"DEBUG: EXCEPTION: {type(e).__name__}: {e}", flush=True)
            import traceback
            traceback.print_exc()
            ErrorNotifier.show_generic_error(f"Unexpected error: {e}")
            self._toast_manager.hide()

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
        pasteboard.clearContents()
        pasteboard.setString_forType_(text, AppKit.NSPasteboardTypeString)

    def register_services(self):
        """Register the services with macOS."""
        print(f"DEBUG register_services: self={self}", flush=True)
        AppKit.NSApp.setServicesProvider_(self)
        print(f"DEBUG register_services: provider set, NSApp={AppKit.NSApp}", flush=True)
        # Verify methods exist
        print(f"DEBUG: has fixGrammarService = {self.respondsToSelector_('fixGrammarService:userData:error:')}", flush=True)

    def update_api_key(self):
        """Update the API client when the API key changes."""
        self._reset_api_client()

    def update_model(self):
        """Update the API client when the model changes."""
        self._reset_api_client()
