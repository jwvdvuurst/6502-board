# 6502 board ROM

Boots the W65C02S into a monitor, with Bob Applegate's Tiny BASIC also resident
in the same 8 KiB ROM. The [Pico C firmware](../pico/README.md) is built separately.
The software interface it must implement is specified in [PROTOCOL.md](PROTOCOL.md).

## Build and outputs

Requires Node.js and cc65 (ca65/ld65). This workspace has the Windows tools in
`tools/cc65/bin`. From the board folder:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File firmware/build.ps1
node firmware/test.js
```

The execution-policy option applies only to that process. The build performs
no downloads or device programming. It generates:

| File in `build/` | Purpose |
|---|---|
| `rom.bin` | Exactly 8192 bytes, CPU addresses `$E000-$FFFF` |
| `eprom32k.bin` | 32768 bytes, ROM at physical offset 0, rest `$FF` |
| `rom.lst`, `rom.map` | Assembly listing and linker placement |
| `images.json` | Image sizes, offsets and SHA-256 hashes |
| `hello.bin`, `hello.hex` | Linked demonstration program at `$0400` |

The 32 KiB image follows DESIGN.md: EPROM A13/A14 are tied low, so the first
8 KiB is visible. This does not establish programmer/device compatibility.

Tested toolchain: ca65/ld65 `V2.19 - Git 77b6484`, Windows snapshot downloaded
2026-11-04 from the [official cc65 download](https://sourceforge.net/projects/cc65/files/cc65-snapshot-win64.zip/download).
Downloaded ZIP SHA-256:
`1a14fab9cd5869c70006fd3c97d59fc5f7e76fd84a4731fc02953017262949cd`.
The snapshot URL changes over time; retain the archive to reproduce this tool version.

## Monitor

All numbers are hexadecimal. Commands are terminated by CR (CR/LF also works).
Monitor input is converted to uppercase. Backspace/Delete removes a character;
Escape clears the pending line, then CR submits it.

| Command | Action |
|---|---|
| `H` | Help |
| `B` | Cold start Tiny BASIC; discards its previous program |
| `D AAAA` | Display 16 bytes; refuses reads crossing into I/O |
| `G AAAA` | Call machine code; an RTS returns to the monitor |
| `K 000N` | Select SRAM bank 0-F; preserves fixed RAM |
| `R` | Send the whole text screen again |
| `L` | Receive Intel HEX records |

Loader records support type 00 (data) and 01 (EOF), up to 32 data bytes per
record. Each complete record is parsed, its checksum checked, and its whole
address span validated before writing anything from that record. Only
`$0400-$77FF` is accepted. Earlier valid records remain if a subsequent record
fails. Overlapping valid records overwrite earlier data. Loading does not run
the program automatically. Type `G` afterward. Banked loading is not provided.

For example, type `L`, send `build/hello.hex` as text, then type `G 0400`.
To package another raw binary already linked at its execution address:

```powershell
node firmware/bin-to-hex.js my-program.bin 0400 > my-program.hex
```

Use ASCII output if running that redirection under Windows PowerShell 5
(which otherwise writes UTF-16), for example pipe to
`Set-Content -Encoding ASCII my-program.hex` instead. The Pico must buffer
USB input and apply backpressure; the CPU receives one requested byte at a time.

## BASIC

This is **Tiny BASIC with signed 16-bit integer arithmetic**, not a floating
point Microsoft BASIC. Use uppercase keywords/variables. It supports `LET`,
`PRINT`, `INPUT`, `IF`, `GOTO`, `GOSUB`, `RETURN`, `REM`, `END`, `LIST`, `RUN`,
`NEW`, `EXIT`, and `FREE()`, `RND()`, `ABS()`. Disk commands are disabled.
`examples/demo.bas` is a sample. Enter `RUN` after entering its numbered lines.
`EXIT` returns to the monitor; Escape does so when BASIC is waiting for input.
Escape cannot interrupt a running infinite loop; use board reset in that case.

The upstream implementation has small eight-entry interpreter/arithmetic/call
stacks and limited error handling. This port bounds input to 79 characters and
rejects program insertion that would reach the screen reservation. It is an
initial firmware version, not a comprehensive BASIC conformance implementation.

## RAM and callable interface

| Address | Owner |
|---|---|
| `$0000-$003F` | Reserved monitor/console zero page (currently `$00-$16`) |
| `$0040-$00BF` | Reserved BASIC zero page (currently through `$87`) |
| `$00C0-$00FF` | Available program zero page |
| `$0100-$01FF` | CPU stack |
| `$0200-$02FF` | Monitor line and HEX record buffers |
| `$0300-$03FF` | BASIC workspace (currently through `$0398`) |
| `$0400-$77FF` | Loaded programs or BASIC program storage; mutually exclusive |
| `$7800-$7FCF` | 2000 ASCII screen cells, 80 columns by 25 rows |
| `$7FD0-$7FFF` | Unused tail; ROM leaves it untouched |
| `$8000-$BFFF` | Bank window; banks 0/1 alias fixed RAM as documented in DESIGN.md |

| ROM address | Call |
|---|---|
| `$E000` | `JSR`: output character in A; CR newline, LF ignored, BS erase |
| `$E003` | `JSR`: blocking keyboard byte returned in A, no echo |
| `$E006` | `JSR`: transmit full screen and current cursor |
| `$E009` | `JMP`: return to monitor; resets CPU stack |
| `$E00C` | `JMP`: cold start BASIC; clears BASIC workspace and resets stack |

Console calls preserve X/Y, clobber A and flags, and use monitor private zero
page. Enter with decimal mode clear and interrupts disabled. Programs must
preserve monitor state and VIA configuration if they call these routines or
return with RTS. No C runtime, relocation, interrupt dispatcher, or OS syscall
layer is implied. NMI and IRQ/BRK vectors enter the monitor; the ROM leaves
interrupts disabled and VIA interrupt enables clear. They are not resumable
debugger traps. Reset is the recovery mechanism after a broken bus transaction.

Programs can write text cells directly, then call `$E006` to publish changes.
Direct writes do not update the ROM cursor. Normal character output publishes
individual cell updates; newline/wrap publishes the cursor, scrolling publishes
a complete frame. Keyboard reads publish the cursor before waiting.

## Validation and limits

`test.js` executes the actual built ROM on
[whscullin/cpu6502](https://github.com/whscullin/cpu6502) in `wdc65c02` mode,
with fixed/banked SRAM and a VIA/Pico handshake model. It checks boot, help,
bank selection, dumping, Intel HEX checksums/types/address bounds, loaded code
and RTS, BASIC arithmetic/LIST/RUN/EXIT/Escape, scrolling, display/SRAM parity,
overlong input, and cold start with nonzero RAM. Tests are instruction-level;
they do not establish electrical timing, metastability margins, USB behavior,
or operation on physical hardware. The Pico implementation has separate portable
C tests and a test replaying actual ROM output bytes; physical integration is untested.

Test dependency source commit: `dca469ab95e38a3fa1a63e95be2f65aa155dc86d`.
To restore test tools in a fresh checkout, clone that repository into
`tools/cpu6502`, check out that commit, and install TypeScript 5.9.3 into
`tools/emulator` using npm with `--ignore-scripts`. Compile it from the board
folder with:

```powershell
node firmware/tools/emulator/node_modules/typescript/bin/tsc firmware/tools/cpu6502/js/cpu6502.ts --module commonjs --target es2020 --outDir firmware/tools/cpu6502/compiled
```

## Source and license

The combined firmware and new board support are distributed under GPL-3.0;
see [COPYING](COPYING). Tiny BASIC is by Bob Applegate/Corsham Technologies,
from [6502-Tiny-BASIC](https://github.com/CorshamTech/6502-Tiny-BASIC), commit
`992fa916f20551cfd1f36877252291355ee73528`. Its README declares GPLv3.
Original sources are retained in `vendor/tinybasic`; `prepare-basic.js` makes
the mechanical ca65 conversion and board changes at build time. Changes include
ROM relocation, separate RAM workspace, board I/O vectors, disabled disk
support, fixed RAM limit, bounded input, and insertion bounds checking.
Retain source, notices and license with distributed firmware.
