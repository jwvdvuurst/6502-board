# 6502-board

A W65C02S computer board with bank-switched SRAM, a ROM monitor and Tiny BASIC,
and a Raspberry Pi Pico USB terminal bridge.

- [Board design and hardware status](DESIGN.md)
- [ROM build, monitor commands, and BASIC](firmware/README.md)
- [Pico C firmware, build, and wiring](pico/README.md)
- [ROM/Pico interface contract](firmware/PROTOCOL.md)
- [Electrical schematic PDF](6502-electrical-draft.pdf)

The hardware is an electrical draft, not fabrication-ready. ROM firmware has
been tested in emulation. Pico C firmware builds to UF2 and passes portable
tests; physical hardware and USB/GPIO integration remain to be validated.

# Agents

Agents must follow the rules, references, skills and agents described in the [AI-hub](C:\Users\JWvdV\Documents\workspace\AI-hub) when this is available.
See also [AGENTS.md](AGENTS.md).
