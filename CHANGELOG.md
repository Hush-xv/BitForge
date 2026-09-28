## v1.12.0 — UI & layout refresh

- Introduced design tokens (`SP` spacing / `RD` radius scales in `theme.py`) and a shared shadow helper (`widgets.make_shadow`); toolbar, display card, expression bar, menus, toasts and aux rows now use the unified scales.
- Reorganized the toolbar into three semantic groups — radix segmented control | sign / lock / bit-width capsule | history / tools / pin — joined by an elastic gap; the bit-width stepper (+ − 8b) is one bordered capsule.
- Radix switch is now a true connected segmented control: only the first and last segments keep outer corners; the active segment fills.
- Aux radix rows lost their permanent border (transparent placeholder keeps geometry) and light up their accent border on hover, lowering visual weight in favour of the bit map.
- Normalized corner radii (display card 20, expression bar / menus 12, toast 16); all behavior, fixed slots (84 px display, 82 px bit map, 277 px keypad) and interaction flows unchanged; full UI suite passes without pin changes.

## v1.11.0 — Internal refactor (behavior unchanged)

- Split the single-file app into the `bitforge/` package: `core` (pure math/expression parsing), `state` (calculator state machine), `render` (display model), `theme`, `widgets`, `main_window`, `app`; `bitforge.py` stays as the launch shim and `python bitforge.py` / `python -m bitforge` both work.
- Extracted `CalculatorState` as the single source of truth for calculator data with pure-Python transitions; undo/redo snapshots are now frozen dataclasses and automatic bit-width sync lives in the state machine instead of the display refresh.
- Consolidated display formatting into `render.compute_display_model` (grouping, font fitting, aux rows, RGB chip, LE preview) applied to widgets through one diffing pass.
- Added `test_core.py`: 455 pure-logic checks (math helpers, expression parser, state machine, undo/redo, randomized word math) that run without Qt/GUI in about a second; the 659-check UI suite remains the release gate.
- All original import APIs (`from bitforge import BitForge, C, ...`) are preserved.

## v1.10.0-r3 — Release hardening

- Added session-only calculator undo/redo (`Ctrl+Z`, `Ctrl+Y`, `Ctrl+Shift+Z`) for numeric input, operations, clear, bit width, radix, sign mode, paste, bit clicks, tools, and expression results.
- Kept expression-editor text undo native to the input box, so calculator-state undo never overwrites in-progress expression edits.
- Hardened signed division/modulo after fixed-width conversion and made negative shift counts report validation errors.
- Reduced top-level layout whitespace while retaining the fixed display and Bit Map heights that keep the keypad stationary.
- Added regression coverage for signed boundary arithmetic, undo/redo state restoration, and responsive layout density.

## v1.10.0 — History sources, Tab radix cycle, follow system theme

- Result history now records its source: keypad operations, tool actions or the expression text.
- `Tab` / `Shift+Tab` cycle HEX -> DEC -> OCT -> BIN; text inputs keep standard focus behaviour.
- New opt-in "follow system" light/dark switch in the Tools > Appearance menu, polling Windows settings.
- Reject keypad values outside the active word width instead of silently wrapping them.
- Persist history sources, dispose theme-specific toast animations, and stop system-theme polling in manual mode.
# Changelog

## v1.9.2 — Precise display grouping

- Replaced font-dependent spaces in grouped values with a fixed 4px gap between byte and nibble groups.
- Revision build: vertically centred single-row Bit Maps and added safe Mask draft feedback.

## v1.9.1 — Display readability

- Replaced wide byte-group spaces in the main display with compact separators.
- Made the display font fit the actual available width, keeping the largest readable size until it is needed to shrink.
- Recalculate the display font after window resizing.

## v1.9.0 — Bit workflow and reliability

- Added optional fixed-width HEX and BIN display formatting.
- Added a non-mutating Little Endian byte-order preview.
- Added common Mask presets, saved Mask favorites, and recent bit-field defaults.
- Added deterministic randomized regression coverage for 8 / 16 / 32 / 64-bit operations and expressions.

## v1.8.1 — Word-width and session update

- Made locked bit widths apply to arithmetic, shifts, NOT, and repeated equals operations.
- Unified number parsing for paste, Mask, and bit-field writing, including signs, separators, prefixes, and `h` suffixes.
- Added explicit 64-bit truncation feedback for pasted values and Masks.
- Restored the last value, Mask, result history, and expression history across restarts.
- Added keyboard focus rings for radix controls.

## v1.8.0 — Release polish

- Fixed Bit Map height so the keypad stays in place across 8 / 16 / 32 / 64-bit modes.
- Centered compact Bit Maps inside the fixed layout slot.
- Preserved the complete editable value after paste or history reload.
- Fixed signed auto-width for pasted, calculated, and expression negative values.
- Allowed single-digit bare hexadecimal values in clipboard paste.
- Improved Mask state badges, history metadata, auxiliary value hover feedback, and menu state hierarchy.
- Added release regression coverage for layout stability, signed values, and clipboard input.

## v1.7.0 — Micro-interactions

- Added key-press ripples and bit-flip flash feedback.
- Added an RGB color swatch preview for the low 24 bits in HEX mode.
- Added a translucent shortcut cheat-sheet overlay on `?`.
- Fixed `?` being swallowed by the `/` operator mapping.

## v1.6.0 — Bit-field mouse selection

- Shift+drag bits to select a contiguous field; a live `SEL hi:lo = value` label appears and click copies the value.
- Selection auto-clears on AC or when the bit width shrinks below the selection.
