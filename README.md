# 6502-board

A W65C02S computer board with bank-switched SRAM, a ROM monitor and Tiny BASIC,
and a Raspberry Pi Pico USB terminal bridge.

- [Board design and hardware status](DESIGN.md)
- [ROM build, monitor commands, and BASIC](firmware/README.md)
- [Interface contract for the future Pico firmware](firmware/PROTOCOL.md)
- [Electrical schematic PDF](6502-electrical-draft.pdf)

The hardware is an electrical draft, not fabrication-ready. ROM firmware has
been tested in emulation; physical hardware validation and Pico firmware remain.
