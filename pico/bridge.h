/**
 * SPDX-License-Identifier: GPL-3.0-only
 * @file bridge.h
 * Portable ROM display decoder, keyboard queue, and parallel-bus state machine.
 */
#ifndef BOARD_BRIDGE_H
#define BOARD_BRIDGE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
enum {
    BOARD_SCREEN_COLUMNS = 80,
    BOARD_SCREEN_CELLS = 2000,
    BOARD_KEY_CAPACITY = 4096,
    BOARD_RECORD_CAPACITY = 2003
};

/** Phases of one CPU-requested byte transfer; ACK is held until REQ falls. */
typedef enum {
    BOARD_BUS_IDLE,   ///< Bus released; wait for a request and optional keyboard data.
    BOARD_BUS_SAMPLE, ///< VIA drives data; allow transceiver input to settle.
    BOARD_BUS_DRIVE,  ///< Pico data latch/direction set with transceiver disabled.
    BOARD_BUS_ENABLE, ///< Pico drives the enabled transceiver before raising ACK.
    BOARD_BUS_ACKED,  ///< Byte accepted; hold ACK and any output data stable.
    BOARD_BUS_FAULT   ///< Invalid direction change; release bus until REQ falls.
} BOARD_BusState;

/** Desired GPIO state; hardware must disable the transceiver before releasing ACK. */
typedef struct {
    bool BOARD_enable;  ///< True means active-low transceiver OE is asserted.
    bool BOARD_output;  ///< True means Pico data GPIOs drive the bus.
    bool BOARD_ack;     ///< Active-high acknowledgement to VIA CB1.
    uint8_t BOARD_data; ///< Byte placed in the Pico output latch before enabling OE.
} BOARD_PinState;

/** All state is owned by the main loop; no dynamic allocation or ISR access. */
typedef struct {
    uint8_t BOARD_screen[BOARD_SCREEN_CELLS]; ///< Raw row-major screen bytes.
    uint16_t BOARD_cursor; ///< Screen cell offset, always less than 2000.

    uint8_t BOARD_record[BOARD_RECORD_CAPACITY]; ///< Uncommitted SLIP payload.
    size_t BOARD_record_size; ///< Number of unescaped bytes collected so far.
    bool BOARD_escaped;       ///< Previous byte was the SLIP escape marker.
    bool BOARD_dropping; ///< Discard this malformed/oversized record until delimiter.
    bool BOARD_synchronized; ///< A delimiter has established a record boundary.
    uint32_t BOARD_accepted; ///< Count of valid, committed display records.
    uint32_t BOARD_rejected; ///< Count of discarded nonempty/malformed records.
    uint32_t BOARD_revision; ///< Changes when a record commits; renderer dirty hint.

    uint8_t BOARD_keys[BOARD_KEY_CAPACITY]; ///< Normalized keyboard ring buffer.
    size_t BOARD_key_head;  ///< Index of the next byte to acknowledge to the CPU.
    size_t BOARD_key_count; ///< Occupied entries; also controls USB backpressure.
    bool BOARD_previous_cr; ///< Suppresses LF immediately following a CR.

    BOARD_BusState BOARD_state; ///< Current phase of the GPIO handshake.
    uint64_t BOARD_deadline;   ///< Earliest time to advance, in monotonic microseconds.
    bool BOARD_direction;      ///< Latched DIR: true means Pico to VIA.
    BOARD_PinState BOARD_pins; ///< Desired pins applied by the Pico hardware adapter.
} BOARD_Bridge;

/** Initialize a blank screen, empty keyboard queue, and released bus.
 * @param BOARD_bridge State to initialize before any other bridge operation.
 */
void BOARD_BridgeInit(BOARD_Bridge *BOARD_bridge);

/** Discard partial framing state without clearing the screen or keyboard queue.
 * @param BOARD_bridge Decoder whose next record must start with a delimiter.
 */
void BOARD_DecoderReset(BOARD_Bridge *BOARD_bridge);

/** Feed one SLIP byte; only complete valid records modify the screen/cursor.
 * @param BOARD_bridge Display decoder and shadow screen.
 * @param BOARD_byte Raw byte received from the VIA.
 */
void BOARD_DisplayByte(BOARD_Bridge *BOARD_bridge, uint8_t BOARD_byte);

/** Queue a keyboard byte, normalizing CR/LF and standalone LF to CR.
 * @param BOARD_bridge Queue receiving host input.
 * @param BOARD_byte Raw host byte; Escape and Delete are preserved.
 * @return True if consumed, false if full; retry a rejected byte later.
 */
bool BOARD_KeyPush(BOARD_Bridge *BOARD_bridge, uint8_t BOARD_byte);

/** Clear queued keys and cancel a prepared byte that has not raised ACK.
 * @param BOARD_bridge Queue and handshake state; an acknowledged byte stays held.
 */
void BOARD_KeysClear(BOARD_Bridge *BOARD_bridge);

/** Advance the nonblocking handshake once, updating desired GPIO outputs.
 * @param BOARD_bridge Bridge state; apply its pins after each call.
 * @param BOARD_request Sampled active-high VIA CA2 request.
 * @param BOARD_direction Sampled PA0 direction: true means Pico to VIA.
 * @param BOARD_data Sampled GPIO data, used only when receiving from the VIA.
 * @param BOARD_now Current monotonic time in microseconds.
 */
void BOARD_BusStep(BOARD_Bridge *BOARD_bridge, bool BOARD_request, bool BOARD_direction,
    uint8_t BOARD_data, uint64_t BOARD_now);

/** Map unsupported display bytes to spaces rather than terminal control codes.
 * @param BOARD_byte Raw screen cell.
 * @return Printable 7-bit ASCII, or a space.
 */
uint8_t BOARD_Printable(uint8_t BOARD_byte);
#endif
