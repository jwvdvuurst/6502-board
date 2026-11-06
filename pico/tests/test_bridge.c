/**
 * SPDX-License-Identifier: GPL-3.0-only
 * @file test_bridge.c
 * Portable tests for display framing, keyboard buffering, GPIO phases, and ANSI.
 */
#include "bridge.h"
#include "terminal.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static BOARD_Bridge bridge;
static void SendPacket(const uint8_t *data, size_t size) {
    /// Feed the same SLIP escaping used by the ROM, not pre-decoded payloads.
    BOARD_DisplayByte(&bridge, 0xc0);
    for (size_t i = 0; i < size; i++) {
        if (data[i] == 0xc0 || data[i] == 0xdb) {
            BOARD_DisplayByte(&bridge, 0xdb);
            BOARD_DisplayByte(&bridge, data[i] == 0xc0 ? 0xdc : 0xdd);
        } else {
            BOARD_DisplayByte(&bridge, data[i]);
        }
    }
    BOARD_DisplayByte(&bridge, 0xc0);
}

static void TestDecoder(void) {
    BOARD_BridgeInit(&bridge);
    uint8_t full[BOARD_RECORD_CAPACITY];
    full[0] = 1;
    memset(full + 1, 'X', BOARD_SCREEN_CELLS);
    full[2001] = 0xcf;
    full[2002] = 7;
    full[193] = 0xc0;
    full[220] = 0xdb;
    SendPacket(full, sizeof(full));
    assert(bridge.BOARD_accepted == 1 && bridge.BOARD_cursor == 1999);
    assert(bridge.BOARD_screen[192] == 0xc0 && bridge.BOARD_screen[219] == 0xdb);
    const uint8_t cell[] = {2, 0xc0, 0, 0xdb}, cursor[] = {3, 0xdb, 0};
    SendPacket(cell, sizeof(cell));
    SendPacket(cursor, sizeof(cursor));
    assert(bridge.BOARD_screen[192] == 0xdb && bridge.BOARD_cursor == 219);
    uint8_t before[BOARD_SCREEN_CELLS];
    memcpy(before, bridge.BOARD_screen, sizeof(before));
    /// An invalid cursor must reject the whole frame without changing screen cells.
    full[2002] = 8;
    SendPacket(full, sizeof(full));
    assert(bridge.BOARD_rejected == 1 &&
        !memcmp(before, bridge.BOARD_screen, sizeof(before)));
    const uint8_t bad[] = {2, 0xd0, 7, 42};
    SendPacket(bad, sizeof(bad));
    assert(bridge.BOARD_rejected == 2);
    SendPacket(cell, 2);
    assert(bridge.BOARD_rejected == 3);
    BOARD_DisplayByte(&bridge, 0xdb);
    BOARD_DisplayByte(&bridge, 0x42);
    BOARD_DisplayByte(&bridge, 0xc0);
    assert(bridge.BOARD_rejected == 4);
    /// An oversized record is ignored through its delimiter; the next one recovers.
    for (unsigned i = 0; i < 3000; i++) {
        BOARD_DisplayByte(&bridge, 1);
    }
    BOARD_DisplayByte(&bridge, 0xc0);
    assert(bridge.BOARD_rejected == 5);
    SendPacket(cell, sizeof(cell));
    assert(bridge.BOARD_accepted == 4);
    BOARD_DecoderReset(&bridge);
    BOARD_DisplayByte(&bridge, 2);
    BOARD_DisplayByte(&bridge, 42);
    assert(bridge.BOARD_record_size == 0);
    SendPacket(cursor, sizeof(cursor));
    assert(bridge.BOARD_cursor == 219);
    puts("PASS atomic full/cell/cursor records, SLIP escapes, bounds, overflow and "
         "resynchronization");
}

static void TestKeys(void) {
    BOARD_BridgeInit(&bridge);
    assert(BOARD_KeyPush(&bridge, '\r'));
    assert(BOARD_KeyPush(&bridge, '\n'));
    assert(BOARD_KeyPush(&bridge, '\n'));
    assert(bridge.BOARD_key_count == 2);
    assert(bridge.BOARD_keys[0] == '\r' && bridge.BOARD_keys[1] == '\r');
    BOARD_KeysClear(&bridge);
    for (unsigned i = 0; i < BOARD_KEY_CAPACITY; i++) {
        assert(BOARD_KeyPush(&bridge, 'A'));
    }
    assert(!BOARD_KeyPush(&bridge, 'B'));
    assert(bridge.BOARD_key_count == BOARD_KEY_CAPACITY);
    BOARD_KeysClear(&bridge);
    assert(!bridge.BOARD_key_count && !bridge.BOARD_previous_cr);
    puts("PASS CR/LF normalization, bounded keyboard queue and backpressure");
}

static void TestBus(void) {
    BOARD_BridgeInit(&bridge);
    BOARD_BusStep(&bridge, true, true, 0, 0); /** no key: keep waiting, bus disabled */
    assert(!bridge.BOARD_pins.BOARD_ack && !bridge.BOARD_pins.BOARD_enable &&
        !bridge.BOARD_pins.BOARD_output);
    BOARD_KeyPush(&bridge, 'K');
    BOARD_BusStep(&bridge, true, true, 0, 1);
    assert(bridge.BOARD_pins.BOARD_output && !bridge.BOARD_pins.BOARD_enable &&
        !bridge.BOARD_pins.BOARD_ack);
    BOARD_BusStep(&bridge, true, true, 0, 2);
    assert(bridge.BOARD_pins.BOARD_enable && !bridge.BOARD_pins.BOARD_ack);
    BOARD_BusStep(&bridge, true, true, 0, 3);
    assert(bridge.BOARD_pins.BOARD_ack && bridge.BOARD_pins.BOARD_data == 'K' &&
        !bridge.BOARD_key_count);
    BOARD_BusStep(&bridge, true, true, 0, 100);
    assert(bridge.BOARD_pins.BOARD_enable && bridge.BOARD_pins.BOARD_ack);
    BOARD_BusStep(&bridge, false, true, 0, 101);
    assert(!bridge.BOARD_pins.BOARD_enable && !bridge.BOARD_pins.BOARD_output &&
        !bridge.BOARD_pins.BOARD_ack);
    /** Cancel a byte before ACK: it must remain queued. */
    BOARD_KeyPush(&bridge, 'Q');
    BOARD_BusStep(&bridge, true, true, 0, 102);
    BOARD_BusStep(&bridge, false, true, 0, 103);
    assert(bridge.BOARD_key_count == 1 && !bridge.BOARD_pins.BOARD_enable);
    BOARD_BusStep(&bridge, true, true, 0, 104);
    BOARD_BusStep(&bridge, true, true, 0, 105);
    BOARD_BusStep(&bridge, false, true, 0, 106);
    assert(bridge.BOARD_key_count == 1);
    /** Closing USB while preparing a key cannot underflow the queue. */
    BOARD_BusStep(&bridge, true, true, 0, 107);
    BOARD_KeysClear(&bridge);
    BOARD_BusStep(&bridge, true, true, 0, 108);
    assert(!bridge.BOARD_key_count && !bridge.BOARD_pins.BOARD_ack);
    BOARD_BusStep(&bridge, false, false, 0, 109);
    BOARD_BusStep(&bridge, true, false, 0xc0, 110);
    assert(bridge.BOARD_pins.BOARD_enable && !bridge.BOARD_pins.BOARD_output);
    BOARD_BusStep(&bridge, true, false, 0xc0, 111);
    assert(bridge.BOARD_pins.BOARD_ack && !bridge.BOARD_pins.BOARD_enable &&
        bridge.BOARD_synchronized);
    BOARD_BusStep(&bridge, false, false, 0, 112);
    BOARD_BusStep(&bridge, true, false, 0, 113);
    BOARD_BusStep(&bridge, true, true, 0, 114);
    assert(bridge.BOARD_state == BOARD_BUS_FAULT && !bridge.BOARD_pins.BOARD_enable &&
        !bridge.BOARD_pins.BOARD_ack);
    BOARD_BusStep(&bridge, true, false, 0, 115);
    assert(bridge.BOARD_state == BOARD_BUS_FAULT);
    BOARD_BusStep(&bridge, false, false, 0, 116);
    assert(bridge.BOARD_state == BOARD_BUS_IDLE);
    puts("PASS bidirectional four-phase handshake, setup delay, cancellation and "
         "direction faults");
}

static void TestTerminal(void) {
    BOARD_Terminal terminal;
    BOARD_BridgeInit(&bridge);
    BOARD_TerminalReset(&terminal);
    bridge.BOARD_screen[0] = 27;
    bridge.BOARD_screen[1] = 'A';
    bridge.BOARD_screen[1999] = 'Z';
    bridge.BOARD_cursor = 1999;
    BOARD_TerminalPrepare(&terminal, &bridge);
    assert(
        terminal.BOARD_pending_size && !memcmp(terminal.BOARD_pending, "\033[?7l", 5));
    size_t size = terminal.BOARD_pending_size;
    BOARD_TerminalPrepare(&terminal, &bridge);
    assert(terminal.BOARD_pending_size == size);
    /** Model a USB write taking one byte at a time. */
    for (unsigned pass = 0; pass < 5000; pass++) {
        if (terminal.BOARD_pending_offset < terminal.BOARD_pending_size) {
            terminal.BOARD_pending_offset++;
        } else {
            BOARD_TerminalPrepare(&terminal, &bridge);
        }
    }
    assert(terminal.BOARD_rendered[0] == ' ' && terminal.BOARD_rendered[1] == 'A' &&
        terminal.BOARD_rendered[1999] == 'Z');
    assert(terminal.BOARD_cursor_valid && terminal.BOARD_cursor == 1999);
    bridge.BOARD_screen[1] = 'B';
    bridge.BOARD_revision++;
    for (unsigned pass = 0; pass < 500; pass++) {
        terminal.BOARD_pending_offset = terminal.BOARD_pending_size;
        BOARD_TerminalPrepare(&terminal, &bridge);
    }
    assert(terminal.BOARD_rendered[1] == 'B');
    BOARD_TerminalReset(&terminal);
    assert(terminal.BOARD_initialize && terminal.BOARD_rendered[1] == 255);
    puts("PASS ANSI sanitization, bottom-right handling, partial USB writes and "
         "reconnect redraw");
}

int main(int argc, char **argv) {
    TestDecoder();
    TestKeys();
    TestBus();
    TestTerminal();
    if (argc == 2) {
        FILE *f = fopen(argv[1], "rb");
        assert(f);
        BOARD_BridgeInit(&bridge);
        int byte;
        uint64_t now = 0;
        while ((byte = fgetc(f)) != EOF) {
            BOARD_BusStep(&bridge, true, false, (uint8_t)byte, now++);
            BOARD_BusStep(&bridge, true, false, (uint8_t)byte, now++);
            assert(bridge.BOARD_pins.BOARD_ack);
            BOARD_BusStep(&bridge, false, false, 0, now++);
        }
        fclose(f);
        assert(!bridge.BOARD_rejected && bridge.BOARD_accepted > 0);
        char screen[BOARD_SCREEN_CELLS + 1];
        memcpy(screen, bridge.BOARD_screen, BOARD_SCREEN_CELLS);
        screen[BOARD_SCREEN_CELLS] = 0;
        assert(strstr(screen, "HELLO FROM A LOADED PROGRAM!"));
        puts("PASS actual 6502 ROM byte stream through C handshake and decoder");
    }
    return 0;
}
