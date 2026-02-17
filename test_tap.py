"""Minimal CGEventTap diagnostic — press any key to see if events arrive."""
import sys
import Quartz
from ApplicationServices import AXIsProcessTrusted


def callback(proxy, event_type, event, user_info):
    keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
    flags = Quartz.CGEventGetFlags(event)
    mod_mask = (
        Quartz.kCGEventFlagMaskCommand
        | Quartz.kCGEventFlagMaskAlternate
        | Quartz.kCGEventFlagMaskControl
        | Quartz.kCGEventFlagMaskShift
    )
    relevant = flags & mod_mask
    print(f"  EVENT type={event_type} keycode={keycode} flags=0x{flags:x} relevant_mods=0x{relevant:x}", flush=True)
    return event


print(f"AXIsProcessTrusted: {AXIsProcessTrusted()}", flush=True)

mask = (
    Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
    | Quartz.CGEventMaskBit(Quartz.kCGEventKeyUp)
    | Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged)
)

print("Creating tap...", flush=True)
tap = Quartz.CGEventTapCreate(
    Quartz.kCGSessionEventTap,
    Quartz.kCGHeadInsertEventTap,
    Quartz.kCGEventTapOptionListenOnly,
    mask,
    callback,
    None,
)
print(f"Tap: {tap}", flush=True)

if tap is None:
    print("FAILED: CGEventTapCreate returned None")
    sys.exit(1)

source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
print(f"RunLoopSource: {source}", flush=True)

run_loop = Quartz.CFRunLoopGetCurrent()
Quartz.CFRunLoopAddSource(run_loop, source, Quartz.kCFRunLoopDefaultMode)
Quartz.CGEventTapEnable(tap, True)

print("Listening for ALL keyboard events. Press any key anywhere...")
print("Press Ctrl+C here to stop.\n", flush=True)

try:
    Quartz.CFRunLoopRun()
except KeyboardInterrupt:
    print("\nDone.")
