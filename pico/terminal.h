/**
 * SPDX-License-Identifier: GPL-3.0-only
 * @file terminal.h
 * Incremental ANSI rendering with bounded, resumable USB output.
 */
#ifndef BOARD_TERMINAL_H
#define BOARD_TERMINAL_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "bridge.h"

/** Renderer snapshot and one pending token; a single main loop owns this state. */
typedef struct {
    uint8_t BOARD_rendered[BOARD_SCREEN_CELLS]; ///< Cells represented by queued output.
    uint16_t BOARD_cursor;   ///< Cursor represented by queued output.
    size_t BOARD_scan;       ///< Cell at which the next dirty scan starts.
    bool BOARD_initialize;   ///< Clear terminal and disable autowrap on next prepare.
    bool BOARD_cursor_valid; ///< False after writing cells, until cursor is restored.
    uint32_t BOARD_rendered_revision; ///< Last fully scanned bridge revision.
    char BOARD_pending[128];   ///< One ANSI sequence or row suffix, possibly in flight.
    size_t BOARD_pending_size; ///< Total bytes in the pending token.
    size_t BOARD_pending_offset; ///< Bytes already accepted by the USB TX queue.
} BOARD_Terminal;

/** Request a complete redraw after startup or a terminal session change.
 * @param BOARD_terminal Renderer to reset; discards any pending USB token.
 */
void BOARD_TerminalReset(BOARD_Terminal *BOARD_terminal);

/** Prepare one output token, leaving an undrained token unchanged.
 * The caller writes pending bytes and advances pending_offset by actual bytes
 * accepted. Rendered cells track queued output, not physical USB delivery;
 * resetting the renderer on disconnect discards that optimistic snapshot.
 * @param BOARD_terminal Renderer and pending token to update.
 * @param BOARD_bridge Desired screen and cursor; never modified.
 */
void BOARD_TerminalPrepare(
    BOARD_Terminal *BOARD_terminal, const BOARD_Bridge *BOARD_bridge);
#endif
