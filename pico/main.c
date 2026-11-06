/**
 * SPDX-License-Identifier: GPL-3.0-only
 * @file main.c
 * Pico GPIO adapter and cooperative USB service loop for the 6502 terminal.
 */
#include "pico/stdlib.h"
#include "tusb.h"
#include "bridge.h"
#include "terminal.h"

enum {
    PIN_REQ = 8,
    PIN_ACK = 9,
    PIN_DIR = 10,
    PIN_OE = 11,
    DATA_MASK = 0xffu,
    USB_INPUT_BUDGET = 32
};

static BOARD_Bridge bridge;
static BOARD_Terminal terminal;
static bool data_driven;
static bool transceiver_enabled;
static bool acknowledged;

static void ApplyPins(void) {
    const BOARD_PinState *pins = &bridge.BOARD_pins;

    /// Break before make: disable the transceiver before changing data direction.
    if (transceiver_enabled &&
        (!pins->BOARD_enable || data_driven != pins->BOARD_output)) {
        gpio_put(PIN_OE, 1);
        transceiver_enabled = false;
    }

    /// Load the output latch before enabling the Pico GPIO drivers.
    if (pins->BOARD_output) {
        gpio_put_masked(DATA_MASK, pins->BOARD_data);
    }
    if (data_driven != pins->BOARD_output) {
        gpio_set_dir_masked(DATA_MASK, pins->BOARD_output ? DATA_MASK : 0);
        data_driven = pins->BOARD_output;
    }
    if (!transceiver_enabled && pins->BOARD_enable) {
        gpio_put(PIN_OE, 0);
        transceiver_enabled = true;
    }

    /// ACK changes last: falling ACK promises that the bus has been released.
    if (acknowledged != pins->BOARD_ack) {
        gpio_put(PIN_ACK, pins->BOARD_ack);
        acknowledged = pins->BOARD_ack;
    }
}

static void ServiceBus(void) {
    /// Sample data and control together, then advance one nonblocking phase.
    uint32_t pins = gpio_get_all();
    BOARD_BusStep(&bridge, (pins >> PIN_REQ) & 1, (pins >> PIN_DIR) & 1, (uint8_t)pins,
        time_us_64());
    ApplyPins();
}

static void InitPins(void) {
    /// External pulls hold the bus safe until these output latches are initialized.
    gpio_init(PIN_OE);
    gpio_put(PIN_OE, 1);
    gpio_set_dir(PIN_OE, GPIO_OUT);
    gpio_init(PIN_ACK);
    gpio_put(PIN_ACK, 0);
    gpio_set_dir(PIN_ACK, GPIO_OUT);

    gpio_init(PIN_REQ);
    gpio_pull_down(PIN_REQ);
    gpio_init(PIN_DIR);
    gpio_pull_down(PIN_DIR);
    for (unsigned pin = 0; pin < 8; pin++) {
        gpio_init(pin);
        gpio_disable_pulls(pin);
    }
}

static void UpdateUsbSession(bool connected) {
    /// Do not replay queued keys from a previous terminal session.
    BOARD_KeysClear(&bridge);
    if (!connected) {
        tud_cdc_read_flush();
    }

    /// Keep the parallel decoder and shadow screen: the 6502 may still transmit.
    /// Reset only the renderer so the next terminal receives a complete redraw.
    BOARD_TerminalReset(&terminal);
    ApplyPins();
}

static void ReceiveUsbInput(void) {
    /// Bound work per pass. When full, leave bytes in TinyUSB so USB OUT applies
    /// backpressure rather than silently dropping characters from a loaded file.
    for (unsigned received = 0; received < USB_INPUT_BUDGET &&
        bridge.BOARD_key_count < BOARD_KEY_CAPACITY && tud_cdc_available();
        received++) {
        uint8_t byte;
        if (tud_cdc_read(&byte, 1) == 1) {
            (void)BOARD_KeyPush(&bridge, byte);
        }
    }
}

static void SendUsbOutput(void) {
    BOARD_TerminalPrepare(&terminal, &bridge);
    size_t remaining = terminal.BOARD_pending_size - terminal.BOARD_pending_offset;
    uint32_t available = tud_cdc_write_available();
    if (!remaining || !available) {
        return;
    }

    /// TinyUSB may accept only part of a token. Resume at the actual accepted byte.
    if (remaining > available) {
        remaining = available;
    }
    terminal.BOARD_pending_offset += tud_cdc_write(
        terminal.BOARD_pending + terminal.BOARD_pending_offset, (uint32_t)remaining);
    tud_cdc_write_flush();
}

int main(void) {
    InitPins();
    BOARD_BridgeInit(&bridge);
    BOARD_TerminalReset(&terminal);
    tusb_init();

    /// The LED indicates initialized firmware, independently of USB DTR state.
    gpio_init(PICO_DEFAULT_LED_PIN);
    gpio_set_dir(PICO_DEFAULT_LED_PIN, GPIO_OUT);
    gpio_put(PICO_DEFAULT_LED_PIN, 1);

    bool connected = false;
    for (;;) {
        ServiceBus();
        tud_task();

        bool current_connection = tud_cdc_connected();
        if (current_connection != connected) {
            UpdateUsbSession(current_connection);
            connected = current_connection;
        }
        if (connected) {
            ReceiveUsbInput();
            SendUsbOutput();
        }

        /// Service the bus even when USB is disconnected or its TX queue is full.
        ServiceBus();
    }
}
