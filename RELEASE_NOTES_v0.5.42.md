# Omni Tuya Local v0.5.42

- Fixed Tuya Cloud sync failing after a successful fetch by filtering integration state objects out of the device reload loop.
- Options-flow cloud sync now waits for completion and displays a translated status/error instead of a blank dialog.
- Add Integration cloud sync now uses the same service path and shows a readable credential/cloud error instead of an unknown error.
