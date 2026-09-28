## v1.14.2 — Pending expression display consistency

- The pending-expression hint in the display card now formats its left operand with the same rules as the main display: `0xFF ×` in HEX, `0b1010 XOR` in BIN, and the signed decimal value (e.g. `-1 +`) when signed mode is on — it previously always showed the raw unsigned decimal integer.

## v1.14.1 — Interaction detail fixes

- Fixed empty-text key events (`"" in "0123456789"` is always true) swallowing F1 / F2 / Delete / arrow keys before their handlers could run — F1 help, F2 expression focus and Delete clear had been unreachable from the physical keyboard since v1.0.
- F2 now also selects the existing expression text, so typing replaces it directly.
- An empty expression input evaluates silently (no error toast) on Enter.
- The bit-field editor's 应用 button is the default (Enter applies).
- Bit-width steppers give feedback when already at 64-bit / 8-bit limits instead of doing nothing silently.
- Fixed DEC thousands-grouping never appearing on animated results: the value animation now repaints the final `DisplayModel` on finish (animation deltas 10–50000 had left ungrouped text on screen until the next refresh).

## v1.14.0 — Expression refill & bit-field editor

- The history menu (⏱) now also lists recent expressions under a "最近表达式" section; picking one refills the expression input via the shared `_load_expression` helper (deduplicated with the input's context menu).
- Replaced the two-step `QInputDialog` flow for bit fields with a single dialog: start bit / width / operation / write value with a live preview of the current field value; ranges clamp against the active word width.
- Extraction and write share the testable `_apply_field` entry point (history source labels unchanged); invalid write values and out-of-range fields report toasts instead of dialogs.
- New coverage: expression refill, field extract/write/reject semantics and recent-range memory (`test_bitforge` §39).

## v1.13.0 — Status micro-line & DEC grouping

- Added a status micro-line in the display card's top-left corner: `32 BIT · UNSIGNED · LOCKED` updates live and never steals mouse events.
- Added an optional thousands-separator display for DEC (Tools > 格式与 Mask); grouping is display-only — the copied value, aux rows and `_display_value` stay raw, and the font-fit measures the grouped text.
- Both preferences persist via QSettings (`format/dec_grouping`).
- Fixed the ± sign button ignoring the persisted signed mode at startup and after theme rebuilds (button state now initializes from `self._signed`).
- Refreshed `docs/` screenshots against the new UI.
- New coverage: status micro-line states, DEC grouping toggle/copy semantics (`test_bitforge` §38) and `dec_group` string helper (`test_core`).

## v1.12.1 — Detail sweep

- Cached display font metrics per size (`render._metrics`) so every keystroke's font fit no longer rebuilds `QFontMetrics` objects.
- `=` with neither a pending operation nor a repeatable last operation now returns immediately, matching the original no-op semantics instead of running a redundant refresh.
- Removed dead surface: unused `HINT` constant and `DisplayText.setBackgroundColor` / `setBorderRadius` no-op stubs.
- Narrowed two bare `except:` clauses (`_si_font` to `Exception`, value animation to `ValueError`).
- Documented the per-radix maximum input length table in `state.input_digit`.
- Startup import profile measured at ~196 ms (siui dominates); the pure-logic suite runs in ~0.24 s — no lazy-import machinery warranted.

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
