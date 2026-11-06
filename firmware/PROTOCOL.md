# ROM/Pico interface v1

This is the contract implemented by [the Pico C firmware](../pico/README.md). The ROM does not implement
USB; it uses the W65C22S at `$C100`. The Pico cannot directly address SRAM.
The 6502 scans its text buffer and sends display records; the Pico reconstructs
the screen and renders it over USB CDC. There is no video hardware.

## Parallel byte handshake

Signals and physical directions follow DESIGN.md: PB0-7 data, PA0 `BUS_DIR`,
CA2 `BUS_REQ`, CB1 `BUS_ACK`. ACK and REQ are active high. Pico owns bus
transceiver `/OE`, held high at idle/reset. ACK idles low. All transfers are
requested by the 6502. Pico must never send an unsolicited byte.

The ROM clears ACR (no port latching, no shift register), disables VIA
interrupts, sets DDRA to `$01`, and polls CB1 flag IFR bit 4. It uses the
no-handshake ORA alias at `$C10F`. CA2 is a manual output; PCR `$0C` means
REQ low/falling ACK edge, `$1C` low/rising ACK edge, `$1E` high/rising ACK
edge, and `$0E` high/falling ACK edge. These modes follow the
[W65C22S datasheet, PCR table and IFR behavior](https://www.westerndesigncenter.com/wdc/documentation/w65c22s.pdf).

Each byte uses a **four-phase level handshake**, replacing the short ACK
pulse in the architecture proposal. Holding ACK until REQ falls avoids lost
edges and provides explicit bus-release confirmation:

1. At idle, REQ=0, ACK=0, transceiver disabled, Pico data pins inputs.
2. 6502 configures DDRB and PA0, clears stale CB1 IFR, selects rising ACK
   detection, then raises REQ. PA0=0 and DDRB=`$FF` requests an output byte;
   PA0=1 and DDRB=`$00` requests a keyboard byte.
3. For output, Pico configures the transceiver to sample VIA data, samples
   the byte, disables the transceiver, then raises ACK. For input, Pico waits
   for a queued USB byte, configures data/direction before enabling the
   transceiver, holds the byte stable, then raises ACK.
4. 6502 observes IFR bit 4. On input, it reads PB while ACK is still high.
   It selects falling ACK detection with REQ still high, clears IFR, then
   lowers REQ.
5. Pico sees REQ low, disables the transceiver, releases its data pins, and
   lowers ACK. It must release the bus **before** lowering ACK.
6. 6502 observes falling ACK via IFR, clears it, and may start another byte.

Output data and direction remain stable while REQ is high. A peripheral may
delay either acknowledgement phase. The ROM waits indefinitely; it does not
reverse a live bus after a timeout. With no Pico, boot initializes SRAM and
waits on the first display transfer. With no keyboard data, Pico leaves ACK
low on an input request. Buffer host input; apply USB backpressure if full.
Never drop loader characters or inject unsolicited XON/XOFF bytes.

Pico must treat REQ dropping before it supplied ACK as cancellation, immediately
disable its bus outputs, and return ACK low. Reset must leave the bus disabled.
Release CPU reset only when Pico has configured its safe idle state. A CPU
reset in a live transaction needs validation with the eventual Pico state
machine; stream framing alone does not prove electrical reset safety.

## 6502 to Pico: display records

Output bytes are **SLIP framed**. `$C0` begins/ends a record. Within a record,
encode `$C0` as `$DB $DC`, and `$DB` as `$DB $DD`. Consecutive delimiters
are harmless. Pico reset or a known parallel-link disconnect must clear the
decoder. USB CDC open/close retains the parallel decoder and shadow screen
because the 6502 can keep transmitting independently of a host terminal. At each delimiter,
reject incomplete/unknown records and begin a new record. This permits recovery
after a truncated frame without treating a payload byte as a command.

After unescaping, records have exactly these lengths:

| Opcode | Payload | Total bytes |
|---|---|---:|
| `$01` | 2000 row-major screen bytes, cursor offset low then high | 2003 |
| `$02` | Cell offset low then high, character byte | 4 |
| `$03` | Cursor offset low then high | 3 |

Offsets range from 0 to 1999. Row=`offset / 80`, column=`offset % 80`.
The full screen is `$7800-$7FCF`; the extra 48 reserved SRAM bytes are not sent.
Normal console output is printable 7-bit ASCII. Direct user-buffer writes can
contain arbitrary bytes; Pico should render unsupported/control values as
spaces rather than executing terminal control sequences from payloads.

Pico maintains a 2000-byte shadow screen and cursor. A full frame replaces
both; a cell record replaces exactly one cell; a cursor record moves the cursor.
The USB side may translate these into ANSI cursor positioning and changed
characters. It must not forward the parallel protocol bytes verbatim to a
terminal. Suppress terminal local echo because the ROM echoes input itself.

At boot, clear/home the host terminal when the first complete full frame
arrives. On reconnect, redraw the retained Pico shadow screen. ROM sends
full frames at boot, on scroll, and on `R`/API refresh. It sends cell changes
for character output and cursor records at line changes and before input.
Direct SRAM edits require an explicit refresh call to become visible.

## Pico to 6502: keyboard bytes

Each input request returns one **raw** keyboard byte; SLIP applies only to
the output direction. Buffer bytes arriving through USB CDC. Configure the
terminal for CR or CR/LF lines. Monitor ignores LF; BASIC maps a standalone
LF to CR, so Pico should normalize CR/LF to one CR before enqueueing.
Backspace `$08` and Delete `$7F` are supported. Escape `$1B` returns from
BASIC to the monitor when BASIC requests a character; it clears a monitor
input line. There is no background break or asynchronous input interrupt.
Use uppercase BASIC input. Do not send terminal arrow-key escape sequences
as editing commands: Escape has the explicit meaning above.

For a binary program, host sends `L` and CR, then Intel HEX text and EOF,
then a `G AAAA` command. The loader accepts maximum 32-byte data records.
For a BASIC program, enter `B`, send uppercase numbered BASIC lines, and
send `RUN`. Future Pico code can provide host-side file selection without
changing either protocol.
