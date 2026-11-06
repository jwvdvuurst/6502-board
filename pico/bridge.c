/**
 * SPDX-License-Identifier: GPL-3.0-only
 * @file bridge.c
 * Portable protocol logic. Hardware access is confined to main.c.
 */
#include "bridge.h"
#include <string.h>

void BOARD_DecoderReset(BOARD_Bridge *BOARD_bridge) {
    BOARD_bridge->BOARD_record_size = 0;
    BOARD_bridge->BOARD_escaped = false;
    BOARD_bridge->BOARD_dropping = false;
    BOARD_bridge->BOARD_synchronized = false;
}

void BOARD_KeysClear(BOARD_Bridge *BOARD_bridge) {
    BOARD_bridge->BOARD_key_head = 0;
    BOARD_bridge->BOARD_key_count = 0;
    BOARD_bridge->BOARD_previous_cr = false;
    /// A prepared key remains queued until ACK; cancel it before clearing the queue.
    /// An already acknowledged key must stay driven until the CPU lowers REQ.
    if (BOARD_bridge->BOARD_state == BOARD_BUS_DRIVE ||
        BOARD_bridge->BOARD_state == BOARD_BUS_ENABLE) {
        BOARD_bridge->BOARD_pins.BOARD_enable = false;
        BOARD_bridge->BOARD_pins.BOARD_output = false;
        BOARD_bridge->BOARD_pins.BOARD_ack = false;
        BOARD_bridge->BOARD_state = BOARD_BUS_IDLE;
    }
}

void BOARD_BridgeInit(BOARD_Bridge *BOARD_bridge) {
    memset(BOARD_bridge, 0, sizeof(*BOARD_bridge));
    memset(BOARD_bridge->BOARD_screen, ' ', sizeof(BOARD_bridge->BOARD_screen));
}

uint8_t BOARD_Printable(uint8_t BOARD_byte) {
    return BOARD_byte >= 32 && BOARD_byte < 127 ? BOARD_byte : ' ';
}

static bool ApplyRecord(BOARD_Bridge *BOARD_bridge) {
    const uint8_t *record = BOARD_bridge->BOARD_record;
    size_t record_size = BOARD_bridge->BOARD_record_size;
    if (record_size == BOARD_RECORD_CAPACITY && record[0] == 1) {
        /// Validate the cursor before committing any cell from a complete frame.
        unsigned cursor = record[2001] | ((unsigned)record[2002] << 8);
        if (cursor >= BOARD_SCREEN_CELLS) {
            return false;
        }
        memcpy(BOARD_bridge->BOARD_screen, record + 1, BOARD_SCREEN_CELLS);
        BOARD_bridge->BOARD_cursor = (uint16_t)cursor;
        return true;
    }
    if ((record_size == 4 && record[0] == 2) || (record_size == 3 && record[0] == 3)) {
        unsigned offset = record[1] | ((unsigned)record[2] << 8);
        if (offset >= BOARD_SCREEN_CELLS) {
            return false;
        }
        if (record[0] == 2) {
            BOARD_bridge->BOARD_screen[offset] = record[3];
        } else {
            BOARD_bridge->BOARD_cursor = (uint16_t)offset;
        }
        return true;
    }
    return false;
}

void BOARD_DisplayByte(BOARD_Bridge *BOARD_bridge, uint8_t BOARD_byte) {
    /// Each delimiter closes the current record and establishes the next boundary.
    /// Discard malformed records as a whole so partial data never reaches the screen.
    if (BOARD_byte == 0xc0) {
        if (BOARD_bridge->BOARD_record_size || BOARD_bridge->BOARD_dropping ||
            BOARD_bridge->BOARD_escaped) {
            if (!BOARD_bridge->BOARD_dropping && !BOARD_bridge->BOARD_escaped &&
                ApplyRecord(BOARD_bridge)) {
                BOARD_bridge->BOARD_accepted++;
                BOARD_bridge->BOARD_revision++;
            } else {
                BOARD_bridge->BOARD_rejected++;
            }
        }
        BOARD_bridge->BOARD_record_size = 0;
        BOARD_bridge->BOARD_dropping = false;
        BOARD_bridge->BOARD_escaped = false;
        BOARD_bridge->BOARD_synchronized = true;
        return;
    }
    /// Ignore startup noise or an oversized payload until a fresh delimiter arrives.
    if (!BOARD_bridge->BOARD_synchronized || BOARD_bridge->BOARD_dropping) {
        return;
    }
    if (BOARD_bridge->BOARD_escaped) {
        BOARD_bridge->BOARD_escaped = false;
        if (BOARD_byte == 0xdc) {
            BOARD_byte = 0xc0;
        } else if (BOARD_byte == 0xdd) {
            BOARD_byte = 0xdb;
        } else {
            BOARD_bridge->BOARD_dropping = true;
            return;
        }
    } else if (BOARD_byte == 0xdb) {
        BOARD_bridge->BOARD_escaped = true;
        return;
    }
    if (BOARD_bridge->BOARD_record_size == sizeof(BOARD_bridge->BOARD_record)) {
        BOARD_bridge->BOARD_dropping = true;
        return;
    }
    BOARD_bridge->BOARD_record[BOARD_bridge->BOARD_record_size++] = BOARD_byte;
}

bool BOARD_KeyPush(BOARD_Bridge *BOARD_bridge, uint8_t BOARD_byte) {
    /// Remember CR across USB packets; only its immediately following LF is suppressed.
    if (BOARD_byte == '\n' && BOARD_bridge->BOARD_previous_cr) {
        BOARD_bridge->BOARD_previous_cr = false;
        return true;
    }
    if (BOARD_bridge->BOARD_key_count == BOARD_KEY_CAPACITY) {
        return false;
    }
    BOARD_bridge->BOARD_previous_cr = BOARD_byte == '\r';
    if (BOARD_byte == '\n') {
        BOARD_byte = '\r';
    }
    size_t tail = (BOARD_bridge->BOARD_key_head + BOARD_bridge->BOARD_key_count) %
        BOARD_KEY_CAPACITY;
    BOARD_bridge->BOARD_keys[tail] = BOARD_byte;
    BOARD_bridge->BOARD_key_count++;
    return true;
}

static void ReleaseBus(BOARD_Bridge *BOARD_bridge) {
    BOARD_bridge->BOARD_pins.BOARD_enable = false;
    BOARD_bridge->BOARD_pins.BOARD_output = false;
    BOARD_bridge->BOARD_pins.BOARD_ack = false;
}

void BOARD_BusStep(BOARD_Bridge *BOARD_bridge, bool BOARD_request, bool BOARD_direction,
    uint8_t BOARD_data, uint64_t BOARD_now) {
    /// REQ low completes a byte or cancels it before ACK. Release outputs in both
    /// cases.
    if (!BOARD_request) {
        ReleaseBus(BOARD_bridge);
        BOARD_bridge->BOARD_state = BOARD_BUS_IDLE;
        return;
    }
    if (BOARD_bridge->BOARD_state != BOARD_BUS_IDLE &&
        BOARD_direction != BOARD_bridge->BOARD_direction) {
        /// Never reverse a live transfer; wait for the CPU to release its request.
        ReleaseBus(BOARD_bridge);
        BOARD_bridge->BOARD_state = BOARD_BUS_FAULT;
    }
    switch (BOARD_bridge->BOARD_state) {
        case BOARD_BUS_IDLE:
            BOARD_bridge->BOARD_direction = BOARD_direction;
            if (BOARD_direction) {
                if (!BOARD_bridge->BOARD_key_count) {
                    return;
                }
                BOARD_bridge->BOARD_pins.BOARD_data =
                    BOARD_bridge->BOARD_keys[BOARD_bridge->BOARD_key_head];
                /// First load the Pico latch and direction with the transceiver
                /// disabled.
                BOARD_bridge->BOARD_pins.BOARD_output = true;
                BOARD_bridge->BOARD_deadline = BOARD_now + 1;
                BOARD_bridge->BOARD_state = BOARD_BUS_DRIVE;
            } else {
                BOARD_bridge->BOARD_pins.BOARD_enable = true;
                BOARD_bridge->BOARD_deadline = BOARD_now + 1;
                BOARD_bridge->BOARD_state = BOARD_BUS_SAMPLE;
            }
            break;
        case BOARD_BUS_SAMPLE:
            /// One microsecond allows VIA-to-Pico data to settle before sampling.
            if (BOARD_now < BOARD_bridge->BOARD_deadline) {
                return;
            }
            BOARD_DisplayByte(BOARD_bridge, BOARD_data);
            BOARD_bridge->BOARD_pins.BOARD_enable = false;
            BOARD_bridge->BOARD_pins.BOARD_ack = true;
            BOARD_bridge->BOARD_state = BOARD_BUS_ACKED;
            break;
        case BOARD_BUS_DRIVE:
            /// Enable only after the Pico latch/direction setup interval has elapsed.
            if (BOARD_now < BOARD_bridge->BOARD_deadline) {
                return;
            }
            BOARD_bridge->BOARD_pins.BOARD_enable = true;
            BOARD_bridge->BOARD_deadline = BOARD_now + 1;
            BOARD_bridge->BOARD_state = BOARD_BUS_ENABLE;
            break;
        case BOARD_BUS_ENABLE:
            /// Consume the queued key only when valid driven data can be acknowledged.
            if (BOARD_now < BOARD_bridge->BOARD_deadline) {
                return;
            }
            BOARD_bridge->BOARD_key_head =
                (BOARD_bridge->BOARD_key_head + 1) % BOARD_KEY_CAPACITY;
            BOARD_bridge->BOARD_key_count--;
            BOARD_bridge->BOARD_pins.BOARD_ack = true;
            BOARD_bridge->BOARD_state = BOARD_BUS_ACKED;
            break;
        case BOARD_BUS_ACKED:
            /// Hold ACK and any driven data stable until REQ falls.
            break;
        case BOARD_BUS_FAULT:
            /// Direction violation: keep the bus released until REQ falls.
            break;
    }
}
