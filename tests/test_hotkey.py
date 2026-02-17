"""Tests for the hotkey module."""
import pytest
from unittest.mock import patch, MagicMock, Mock
from vox.hotkey import (
    get_key_code,
    parse_modifiers,
    HotKeyManager,
    has_accessibility_permission,
    request_accessibility_permission,
    create_hotkey_manager,
    KEY_CODES,
    MODIFIER_FLAGS,
    ALL_MODIFIER_FLAGS_MASK,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskAlternate,
    kCGEventFlagMaskControl,
    kCGEventFlagMaskShift,
    kCGEventKeyDown,
    kCGEventTapDisabledByTimeout,
    kCGEventTapDisabledByUserInput,
    kCGKeyboardEventKeycode,
    kCGKeyboardEventAutorepeat,
)


class TestKeyCodeMapping:
    """Tests for KEY_CODES constant."""

    def test_key_codes_contains_expected_keys(self):
        """Test that KEY_CODES has common keys."""
        expected_keys = ['a', 'b', 'c', 'd', 'v', 'r', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
        for key in expected_keys:
            assert key in KEY_CODES


class TestGetKeyCode:
    """Tests for get_key_code function."""

    def test_get_key_code_lowercase(self):
        """Test getting key code for lowercase letters."""
        assert get_key_code('a') == 0x00
        assert get_key_code('b') == 0x0B
        assert get_key_code('c') == 0x08
        assert get_key_code('d') == 0x02
        assert get_key_code('v') == 0x09
        assert get_key_code('r') == 0x0F

    def test_get_key_code_uppercase(self):
        """Test getting key code for uppercase letters (should work same as lowercase)."""
        assert get_key_code('A') == 0x00
        assert get_key_code('V') == 0x09
        assert get_key_code('R') == 0x0F

    def test_get_key_code_numbers(self):
        """Test getting key code for number keys."""
        assert get_key_code('0') == 0x1D
        assert get_key_code('1') == 0x12
        assert get_key_code('5') == 0x17
        assert get_key_code('9') == 0x19

    def test_get_key_code_empty_string(self):
        """Test that empty string returns default (V key)."""
        assert get_key_code('') == 0x09

    def test_get_key_code_unknown_key(self):
        """Test that unknown key uses first character."""
        # 'unknown' starts with 'u', which has key code 0x20
        assert get_key_code('unknown') == 0x20


class TestParseModifiers:
    """Tests for parse_modifiers function."""

    def test_parse_single_modifier_cmd(self):
        """Test parsing single cmd modifier."""
        result = parse_modifiers('cmd')
        assert result == kCGEventFlagMaskCommand

    def test_parse_single_modifier_command(self):
        """Test parsing single command modifier (alias for cmd)."""
        result = parse_modifiers('command')
        assert result == kCGEventFlagMaskCommand

    def test_parse_single_modifier_option(self):
        """Test parsing single option modifier."""
        result = parse_modifiers('option')
        assert result == kCGEventFlagMaskAlternate

    def test_parse_single_modifier_opt(self):
        """Test parsing single opt modifier (alias for option)."""
        result = parse_modifiers('opt')
        assert result == kCGEventFlagMaskAlternate

    def test_parse_single_modifier_alt(self):
        """Test parsing single alt modifier (alias for option)."""
        result = parse_modifiers('alt')
        assert result == kCGEventFlagMaskAlternate

    def test_parse_single_modifier_control(self):
        """Test parsing single control modifier."""
        result = parse_modifiers('control')
        assert result == kCGEventFlagMaskControl

    def test_parse_single_modifier_ctrl(self):
        """Test parsing single ctrl modifier (alias for control)."""
        result = parse_modifiers('ctrl')
        assert result == kCGEventFlagMaskControl

    def test_parse_single_modifier_shift(self):
        """Test parsing single shift modifier."""
        result = parse_modifiers('shift')
        assert result == kCGEventFlagMaskShift

    def test_parse_combined_modifiers_with_plus(self):
        """Test parsing combined modifiers with + separator."""
        result = parse_modifiers('cmd+shift')
        assert result == (kCGEventFlagMaskCommand | kCGEventFlagMaskShift)

    def test_parse_combined_modifiers_with_space(self):
        """Test parsing combined modifiers with space separator."""
        result = parse_modifiers('cmd shift')
        assert result == (kCGEventFlagMaskCommand | kCGEventFlagMaskShift)

    def test_parse_combined_modifiers_mixed_separator(self):
        """Test parsing combined modifiers with mixed separators."""
        result = parse_modifiers('cmd+shift control')
        assert result == (kCGEventFlagMaskCommand | kCGEventFlagMaskShift | kCGEventFlagMaskControl)

    def test_parse_modifiers_case_insensitive(self):
        """Test that modifier parsing is case insensitive."""
        result = parse_modifiers('CMD+SHIFT')
        assert result == (kCGEventFlagMaskCommand | kCGEventFlagMaskShift)

    def test_parse_empty_modifiers(self):
        """Test parsing empty string returns 0."""
        result = parse_modifiers('')
        assert result == 0


class TestModifierFlagsMapping:
    """Tests for MODIFIER_FLAGS constant and ALL_MODIFIER_FLAGS_MASK."""

    def test_modifier_flags_contains_all_aliases(self):
        """Test that MODIFIER_FLAGS covers all known aliases."""
        assert 'cmd' in MODIFIER_FLAGS
        assert 'command' in MODIFIER_FLAGS
        assert 'option' in MODIFIER_FLAGS
        assert 'opt' in MODIFIER_FLAGS
        assert 'alt' in MODIFIER_FLAGS
        assert 'control' in MODIFIER_FLAGS
        assert 'ctrl' in MODIFIER_FLAGS
        assert 'shift' in MODIFIER_FLAGS

    def test_all_modifier_flags_mask(self):
        """Test that ALL_MODIFIER_FLAGS_MASK includes all four modifier bits."""
        assert ALL_MODIFIER_FLAGS_MASK & kCGEventFlagMaskCommand
        assert ALL_MODIFIER_FLAGS_MASK & kCGEventFlagMaskAlternate
        assert ALL_MODIFIER_FLAGS_MASK & kCGEventFlagMaskControl
        assert ALL_MODIFIER_FLAGS_MASK & kCGEventFlagMaskShift


class TestAccessibilityPermission:
    """Tests for accessibility permission functions."""

    def test_has_accessibility_permission_true(self):
        """Test has_accessibility_permission returns True when granted."""
        with patch('vox.hotkey.AXIsProcessTrusted', return_value=True):
            assert has_accessibility_permission() is True

    def test_has_accessibility_permission_false(self):
        """Test has_accessibility_permission returns False when denied."""
        with patch('vox.hotkey.AXIsProcessTrusted', return_value=False):
            assert has_accessibility_permission() is False

    def test_has_accessibility_permission_exception(self):
        """Test has_accessibility_permission handles exceptions."""
        with patch('vox.hotkey.AXIsProcessTrusted', side_effect=Exception("Test error")):
            assert has_accessibility_permission() is False

    def test_request_accessibility_permission_granted(self):
        """Test request_accessibility_permission when granted."""
        with patch('vox.hotkey.AXIsProcessTrustedWithOptions', return_value=True):
            assert request_accessibility_permission() is True

    def test_request_accessibility_permission_denied(self):
        """Test request_accessibility_permission when denied."""
        with patch('vox.hotkey.AXIsProcessTrustedWithOptions', return_value=False):
            assert request_accessibility_permission() is False

    def test_request_accessibility_permission_exception(self):
        """Test request_accessibility_permission handles exceptions."""
        with patch('vox.hotkey.AXIsProcessTrustedWithOptions', side_effect=Exception("Test error")):
            assert request_accessibility_permission() is False


class TestHotKeyManager:
    """Tests for HotKeyManager class."""

    def test_init_default_values(self):
        """Test HotKeyManager initialization with default values."""
        manager = HotKeyManager()
        assert manager._callback is None
        assert manager._enabled is True
        assert manager._modifiers_str == "option"
        assert manager._key_str == "v"
        assert manager._target_key_code == 0
        assert manager._target_modifiers == 0
        assert manager._is_registered is False
        assert manager._tap is None
        assert manager._tap_callback is None
        assert manager._run_loop_source is None
        assert manager._run_loop is None
        assert manager._tap_thread is None

    def test_set_callback(self):
        """Test setting the callback function."""
        manager = HotKeyManager()
        callback = lambda: None
        manager.set_callback(callback)
        assert manager._callback == callback

    def test_set_hotkey(self):
        """Test setting the hot key combination."""
        manager = HotKeyManager()
        manager.set_hotkey('cmd+shift', 'r')
        assert manager._modifiers_str == 'cmd+shift'
        assert manager._key_str == 'r'

    def test_set_enabled_true(self):
        """Test enabling the hot key manager."""
        manager = HotKeyManager()
        manager._enabled = False
        manager.set_enabled(True)
        assert manager._enabled is True

    def test_set_enabled_false_unregisters(self):
        """Test disabling the hot key manager unregisters it."""
        manager = HotKeyManager()
        manager._is_registered = True
        with patch.object(manager, 'unregister_hotkey') as mock_unreg:
            manager.set_enabled(False)
            mock_unreg.assert_called_once()
            assert manager._enabled is False

    def test_set_enabled_false_not_registered(self):
        """Test disabling when not registered doesn't call unregister."""
        manager = HotKeyManager()
        manager._is_registered = False
        with patch.object(manager, 'unregister_hotkey') as mock_unreg:
            manager.set_enabled(False)
            mock_unreg.assert_not_called()

    def test_unregister_hotkey_when_registered(self):
        """Test unregistering the hot key when registered."""
        manager = HotKeyManager()
        manager._is_registered = True
        manager._tap = MagicMock()
        manager._run_loop = MagicMock()
        manager._tap_thread = MagicMock()

        with patch('vox.hotkey.CGEventTapEnable') as mock_tap_enable, \
             patch('vox.hotkey.CoreFoundation') as mock_cf:
            manager.unregister_hotkey()
            mock_tap_enable.assert_called_once()
            mock_cf.CFRunLoopStop.assert_called_once()
            assert manager._tap is None
            assert manager._tap_callback is None
            assert manager._run_loop_source is None
            assert manager._run_loop is None
            assert manager._tap_thread is None
            assert manager._is_registered is False

    def test_unregister_hotkey_when_not_registered(self):
        """Test unregistering when not registered does nothing."""
        manager = HotKeyManager()
        manager._is_registered = False
        manager.unregister_hotkey()
        # Should not raise any exception

    def test_unregister_hotkey_exception_handling(self):
        """Test unregister_hotkey handles exceptions gracefully."""
        manager = HotKeyManager()
        manager._is_registered = True
        manager._tap = MagicMock()
        manager._run_loop = MagicMock()
        manager._tap_thread = MagicMock()

        with patch('vox.hotkey.CGEventTapEnable', side_effect=Exception("Test error")):
            # Should not raise, just print error
            manager.unregister_hotkey()

    def test_reregister_hotkey(self):
        """Test reregistering the hot key."""
        manager = HotKeyManager()
        with patch.object(manager, 'unregister_hotkey') as mock_unreg, \
             patch.object(manager, 'register_hotkey', return_value=True) as mock_reg:
            result = manager.reregister_hotkey()
            mock_unreg.assert_called_once()
            mock_reg.assert_called_once()
            assert result is True

    def test_register_hotkey_when_disabled(self):
        """Test registering when disabled returns False."""
        manager = HotKeyManager()
        manager._enabled = False
        result = manager.register_hotkey()
        assert result is False

    def test_register_hotkey_already_registered(self):
        """Test registering when already registered returns True."""
        manager = HotKeyManager()
        manager._enabled = True
        manager._is_registered = True
        result = manager.register_hotkey()
        assert result is True

    def test_register_hotkey_no_permission_with_dialog(self):
        """Test registering without permission shows dialog."""
        manager = HotKeyManager()
        manager._enabled = True

        with patch('vox.hotkey.has_accessibility_permission', return_value=False), \
             patch('vox.hotkey.request_accessibility_permission', return_value=False), \
             patch.object(manager, '_show_accessibility_dialog') as mock_dialog:
            result = manager.register_hotkey()
            mock_dialog.assert_called_once()
            assert result is False

    def test_register_hotkey_success(self):
        """Test successful hot key registration via CGEventTap."""
        manager = HotKeyManager()
        manager._enabled = True
        manager.set_hotkey('cmd', 'd')

        mock_tap = MagicMock()
        mock_rls = MagicMock()

        with patch('vox.hotkey.has_accessibility_permission', return_value=True), \
             patch('vox.hotkey.CGEventTapCreate', return_value=mock_tap), \
             patch('vox.hotkey.CGEventMaskBit', return_value=0x400), \
             patch('vox.hotkey.CoreFoundation') as mock_cf, \
             patch('vox.hotkey.threading') as mock_threading:
            mock_cf.CFMachPortCreateRunLoopSource.return_value = mock_rls
            mock_thread = MagicMock()
            mock_threading.Thread.return_value = mock_thread

            result = manager.register_hotkey()
            assert result is True
            assert manager._is_registered is True
            assert manager._tap is mock_tap
            assert manager._run_loop_source is mock_rls
            mock_thread.start.assert_called_once()

    def test_register_hotkey_tap_creation_fails(self):
        """Test hot key registration when CGEventTapCreate returns None."""
        manager = HotKeyManager()
        manager._enabled = True

        with patch('vox.hotkey.has_accessibility_permission', return_value=True), \
             patch('vox.hotkey.CGEventTapCreate', return_value=None), \
             patch('vox.hotkey.CGEventMaskBit', return_value=0x400), \
             patch.object(manager, '_show_accessibility_dialog') as mock_dialog:
            result = manager.register_hotkey()
            assert result is False
            mock_dialog.assert_called_once()

    def test_register_hotkey_exception_handling(self):
        """Test register_hotkey handles exceptions gracefully."""
        manager = HotKeyManager()
        manager._enabled = True

        with patch('vox.hotkey.has_accessibility_permission', return_value=True), \
             patch('vox.hotkey.CGEventTapCreate', side_effect=Exception("Tap error")), \
             patch('vox.hotkey.CGEventMaskBit', return_value=0x400):
            result = manager.register_hotkey()
            assert result is False


class TestHandleCGEvent:
    """Tests for _handle_cg_event method."""

    def _make_manager(self):
        manager = HotKeyManager()
        manager._target_key_code = 0x02  # D
        manager._target_modifiers = kCGEventFlagMaskCommand
        manager._enabled = True
        manager._callback = MagicMock()
        manager._tap = MagicMock()
        return manager

    def test_handle_disabled_by_timeout_reenables(self):
        """Test that kCGEventTapDisabledByTimeout re-enables the tap."""
        manager = self._make_manager()
        mock_event = MagicMock()

        with patch('vox.hotkey.CGEventTapEnable') as mock_enable:
            result = manager._handle_cg_event(None, kCGEventTapDisabledByTimeout, mock_event)
            mock_enable.assert_called_once_with(manager._tap, True)
            assert result is mock_event

    def test_handle_disabled_by_user_input_passes_through(self):
        """Test that kCGEventTapDisabledByUserInput passes event through."""
        manager = self._make_manager()
        mock_event = MagicMock()
        result = manager._handle_cg_event(None, kCGEventTapDisabledByUserInput, mock_event)
        assert result is mock_event

    def test_handle_non_keydown_passes_through(self):
        """Test that non-keydown events pass through."""
        manager = self._make_manager()
        mock_event = MagicMock()
        result = manager._handle_cg_event(None, 999, mock_event)
        assert result is mock_event
        manager._callback.assert_not_called()

    def test_handle_wrong_keycode_passes_through(self):
        """Test that wrong key code passes through."""
        manager = self._make_manager()
        mock_event = MagicMock()

        with patch('vox.hotkey.CGEventGetIntegerValueField', return_value=0x09):  # V, not D
            result = manager._handle_cg_event(None, kCGEventKeyDown, mock_event)
            assert result is mock_event
            manager._callback.assert_not_called()

    def test_handle_autorepeat_passes_through(self):
        """Test that key repeat events pass through."""
        manager = self._make_manager()
        mock_event = MagicMock()

        def mock_get_field(event, field):
            if field == kCGKeyboardEventKeycode:
                return 0x02  # D
            if field == kCGKeyboardEventAutorepeat:
                return 1
            return 0

        with patch('vox.hotkey.CGEventGetIntegerValueField', side_effect=mock_get_field):
            result = manager._handle_cg_event(None, kCGEventKeyDown, mock_event)
            assert result is mock_event
            manager._callback.assert_not_called()

    def test_handle_wrong_modifiers_passes_through(self):
        """Test that wrong modifier flags pass through."""
        manager = self._make_manager()
        mock_event = MagicMock()

        def mock_get_field(event, field):
            if field == kCGKeyboardEventKeycode:
                return 0x02  # D
            if field == kCGKeyboardEventAutorepeat:
                return 0
            return 0

        with patch('vox.hotkey.CGEventGetIntegerValueField', side_effect=mock_get_field), \
             patch('vox.hotkey.CGEventGetFlags', return_value=kCGEventFlagMaskAlternate):  # Option, not Cmd
            result = manager._handle_cg_event(None, kCGEventKeyDown, mock_event)
            assert result is mock_event
            manager._callback.assert_not_called()

    def test_handle_matching_hotkey_dispatches_callback(self):
        """Test that matching hotkey dispatches callback to main thread."""
        manager = self._make_manager()
        mock_event = MagicMock()

        def mock_get_field(event, field):
            if field == kCGKeyboardEventKeycode:
                return 0x02  # D
            if field == kCGKeyboardEventAutorepeat:
                return 0
            return 0

        with patch('vox.hotkey.CGEventGetIntegerValueField', side_effect=mock_get_field), \
             patch('vox.hotkey.CGEventGetFlags', return_value=kCGEventFlagMaskCommand), \
             patch('vox.hotkey.AppKit') as mock_appkit:
            mock_queue = MagicMock()
            mock_appkit.NSOperationQueue.mainQueue.return_value = mock_queue

            result = manager._handle_cg_event(None, kCGEventKeyDown, mock_event)
            assert result is mock_event
            mock_queue.addOperationWithBlock_.assert_called_once_with(manager._callback)

    def test_handle_disabled_manager_does_not_dispatch(self):
        """Test that disabled manager does not dispatch callback."""
        manager = self._make_manager()
        manager._enabled = False
        mock_event = MagicMock()

        def mock_get_field(event, field):
            if field == kCGKeyboardEventKeycode:
                return 0x02
            if field == kCGKeyboardEventAutorepeat:
                return 0
            return 0

        with patch('vox.hotkey.CGEventGetIntegerValueField', side_effect=mock_get_field), \
             patch('vox.hotkey.CGEventGetFlags', return_value=kCGEventFlagMaskCommand):
            result = manager._handle_cg_event(None, kCGEventKeyDown, mock_event)
            assert result is mock_event
            manager._callback.assert_not_called()

    def test_handle_exception_returns_event(self):
        """Test that exceptions in callback return event to avoid breaking event stream."""
        manager = self._make_manager()
        mock_event = MagicMock()

        with patch('vox.hotkey.CGEventGetIntegerValueField', side_effect=Exception("boom")):
            result = manager._handle_cg_event(None, kCGEventKeyDown, mock_event)
            assert result is mock_event


class TestShowAccessibilityDialog:
    """Tests for _show_accessibility_dialog method."""

    def test_show_accessibility_dialog_opens_settings(self):
        """Test dialog opens System Settings when first button clicked."""
        manager = HotKeyManager()

        with patch('vox.hotkey.AppKit') as mock_appkit:
            mock_alert = MagicMock()
            mock_appkit.NSAlert.alloc().init.return_value = mock_alert
            mock_appkit.NSAlertFirstButtonReturn = 1000
            mock_appkit.NSAlertSecondButtonReturn = 1001
            mock_appkit.NSAlertStyleWarning = 2
            mock_alert.runModal.return_value = 1000  # First button

            mock_workspace = MagicMock()
            mock_appkit.NSWorkspace.sharedWorkspace.return_value = mock_workspace
            mock_appkit.NSURL.URLWithString_.return_value = MagicMock()

            manager._show_accessibility_dialog()

            mock_workspace.openURL_.assert_called_once()

    def test_show_accessibility_dialog_cancels(self):
        """Test dialog cancels when second button clicked."""
        manager = HotKeyManager()

        with patch('vox.hotkey.AppKit') as mock_appkit:
            mock_alert = MagicMock()
            mock_appkit.NSAlert.alloc().init.return_value = mock_alert
            mock_appkit.NSAlertFirstButtonReturn = 1000
            mock_appkit.NSAlertSecondButtonReturn = 1001
            mock_appkit.NSAlertStyleWarning = 2
            mock_alert.runModal.return_value = 1001  # Second button

            mock_workspace = MagicMock()
            mock_appkit.NSWorkspace.sharedWorkspace.return_value = mock_workspace

            manager._show_accessibility_dialog()

            mock_workspace.openURL_.assert_not_called()


class TestCreateHotkeyManager:
    """Tests for create_hotkey_manager factory function."""

    def test_create_hotkey_manager_returns_instance(self):
        """Test factory function returns HotKeyManager instance."""
        manager = create_hotkey_manager()
        assert isinstance(manager, HotKeyManager)
