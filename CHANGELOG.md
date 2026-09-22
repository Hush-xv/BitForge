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

