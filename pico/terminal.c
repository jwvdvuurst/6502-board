/**
 * SPDX-License-Identifier: GPL-3.0-only
 * @file terminal.c
 * Render screen differences as resumable ANSI output without blocking USB writes.
 */
#include "terminal.h"
#include <stdio.h>
#include <string.h>

void BOARD_TerminalReset(BOARD_Terminal *BOARD_terminal) {
    memset(BOARD_terminal, 0, sizeof(*BOARD_terminal));
    memset(
        BOARD_terminal->BOARD_rendered, 0xff, sizeof(BOARD_terminal->BOARD_rendered));
    BOARD_terminal->BOARD_initialize = true;
}

void BOARD_TerminalPrepare(
    BOARD_Terminal *BOARD_terminal, const BOARD_Bridge *BOARD_bridge) {
    if (BOARD_terminal->BOARD_pending_offset != BOARD_terminal->BOARD_pending_size) {
        return;
    }
    BOARD_terminal->BOARD_pending_offset = 0;
    BOARD_terminal->BOARD_pending_size = 0;
    /// Avoid rescanning 2000 cells on every idle main-loop iteration.
    if (!BOARD_terminal->BOARD_initialize && BOARD_terminal->BOARD_cursor_valid &&
        BOARD_terminal->BOARD_rendered_revision == BOARD_bridge->BOARD_revision) {
        return;
    }
    if (BOARD_terminal->BOARD_initialize) {
        /// Disable autowrap so writing the bottom-right cell cannot scroll the screen.
        const char start[] = "\033[?7l\033[2J\033[H";
        memcpy(BOARD_terminal->BOARD_pending, start, sizeof(start) - 1);
        BOARD_terminal->BOARD_pending_size = sizeof(start) - 1;
        BOARD_terminal->BOARD_initialize = false;
        return;
    }
    for (size_t examined = 0; examined < BOARD_SCREEN_CELLS; examined++) {
        size_t cell = BOARD_terminal->BOARD_scan;
        BOARD_terminal->BOARD_scan = (cell + 1) % BOARD_SCREEN_CELLS;
        if (BOARD_terminal->BOARD_rendered[cell] ==
            BOARD_Printable(BOARD_bridge->BOARD_screen[cell])) {
            continue;
        }
        int length = snprintf(BOARD_terminal->BOARD_pending,
            sizeof(BOARD_terminal->BOARD_pending), "\033[%u;%uH",
            (unsigned)(cell / BOARD_SCREEN_COLUMNS + 1),
            (unsigned)(cell % BOARD_SCREEN_COLUMNS + 1));
        /// Snapshot the rest of this row into one token. Later screen changes are
        /// picked up on the next scan, without altering a partially sent token.
        size_t row_end = (cell / BOARD_SCREEN_COLUMNS + 1) * BOARD_SCREEN_COLUMNS;
        for (; cell < row_end; cell++) {
            uint8_t character = BOARD_Printable(BOARD_bridge->BOARD_screen[cell]);
            BOARD_terminal->BOARD_pending[length++] = (char)character;
            BOARD_terminal->BOARD_rendered[cell] = character;
        }
        BOARD_terminal->BOARD_pending_size = (size_t)length;
        BOARD_terminal->BOARD_scan = row_end % BOARD_SCREEN_CELLS;
        BOARD_terminal->BOARD_cursor_valid = false;
        return;
    }
    BOARD_terminal->BOARD_rendered_revision = BOARD_bridge->BOARD_revision;
    /// Row output moves the physical terminal cursor; restore the ROM cursor last.
    if (!BOARD_terminal->BOARD_cursor_valid ||
        BOARD_terminal->BOARD_cursor != BOARD_bridge->BOARD_cursor) {
        BOARD_terminal->BOARD_pending_size =
            (size_t)snprintf(BOARD_terminal->BOARD_pending,
                sizeof(BOARD_terminal->BOARD_pending), "\033[%u;%uH",
                (unsigned)(BOARD_bridge->BOARD_cursor / BOARD_SCREEN_COLUMNS + 1),
                (unsigned)(BOARD_bridge->BOARD_cursor % BOARD_SCREEN_COLUMNS + 1));
        BOARD_terminal->BOARD_cursor = BOARD_bridge->BOARD_cursor;
        BOARD_terminal->BOARD_cursor_valid = true;
    }
}
