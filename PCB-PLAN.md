# 6502 Board: Roadmap to a Complete PCB Design

## Purpose and current position

This plan takes the project from its current documented state to a reviewed
PCB design with Gerber and drill files ready for the owner to upload to a board
fabrication service such as PCBWay. Assembly is a hybrid process: the owner
self-assembles the through-hole components; any residual SMD components are
to be assembled by the service where offered. It does **not** authorize
ordering boards, programming devices, or claiming the design is electrically
safe or proven.

The project already has:

- A W65C02S/W65C22S electrical-draft schematic with the proposed memory map,
  SRAM bank switching, ROM, Pico harness, and bus transceiver.
- A ROM monitor/Tiny BASIC firmware image and emulator tests.
- Pico bridge firmware, portable tests, a target build, and a test that replays
  actual ROM output through the Pico protocol implementation.
- KiCad ERC and netlist checks documented in [DESIGN.md](./DESIGN.md).

The project does **not** yet have a `.kicad_pcb` board. The electrical design
still has component, power, timing, sourcing, and power-sequencing questions.
The electrical schematic and its documentation should therefore be treated as
a design draft, not as a layout-ready netlist. See [DESIGN.md](./DESIGN.md),
[firmware/README.md](./firmware/README.md), and
[pico/README.md](./pico/README.md) for the existing contracts and evidence.

## How to use this plan

- Work through the phases in order. A phase is complete only when its exit
  criteria are met and its evidence is recorded.
- Keep each unresolved hardware assumption visible. Do not silently turn a
  provisional symbol, footprint, voltage, timing value, or board dimension into
  a production decision.
- Use exact manufacturer orderable part numbers and datasheets for electrical
  and footprint verification. A library entry or a successful ERC/DRC is not
  proof of suitability.
- Make decisions reversible until the relevant human review gate is approved.
  Keep the schematic, PCB, generated reports, and this plan in version control;
  do not commit generated caches or local tool installations.
- An AI agent can prepare analyses, check connectivity, maintain constraints,
  and run CAD checks. A human with hardware design responsibility must approve
  part choices, electrical margins, mechanical fit, exceptions, and the final
  manufacturing package.
- Unless the project owner explicitly revises the existing requirement in
  [DESIGN.md](./DESIGN.md), all main-board ICs remain socketed through-hole DIP
  parts. Service-assembled SMD is for residual non-IC components that remain
  after honoring that requirement; do not convert an IC to SMD by assumption.

## Roles and decision ownership

| Role | Responsibility |
|---|---|
| Project owner | Confirms intended use, budget, connector/mechanical needs, fabrication and assembly preferences, and accepts schedule/sourcing trade-offs. |
| Hardware reviewer | Verifies component ratings, pinouts, timing, reset/power behavior, signal integrity assumptions, and the final design. Prefer a qualified hardware engineer for board release. |
| CAD implementer (human or AI-assisted) | Maintains schematic/PCB consistency, footprints, constraints, layout, and reproducible validation reports. |
| Firmware owner | Confirms the memory map, ROM placement/vectors, VIA register behavior, Pico harness protocol, reset expectations, and test coverage remain valid as hardware changes. |
| Fabricator/assembler (when selected) | Supplies current capability, layer stack, drill, solder-mask, assembly, and deliverable requirements. Their written specifications govern fabrication settings. |

The project owner may hold several roles, but should still explicitly review
each approval gate rather than treating an automated check as approval.

## Phase 0 — Establish the design baseline and release target

**Goal:** Agree what “complete PCB design” means for this revision and preserve
a clean, traceable starting point.

### Work

1. Identify the authoritative electrical schematic. Keep
   `6502-electrical-draft.kicad_sch` as the working electrical source; the
   separate `6502-board.kicad_sch` is documented as a conceptual block diagram.
2. Record the KiCad version, project files, symbol libraries, schematic
   generator (if used), and commands currently used for netlist/ERC checks.
3. Record the chosen assembly split:
   - owner installs all through-hole parts, with each main-board IC installed
     in its required socket;
   - the board service fabricates the bare PCB and may assemble residual SMD
     parts, subject to the selected service's capabilities and parts process;
   - clearly mark which BOM items are service-assembled, self-assembled, or
     not populated at that stage.
4. Define the required release output: reviewed editable KiCad project and
   `.kicad_pcb`, Gerbers for the agreed copper/mask/silkscreen/outline layers,
   drill files, fabrication notes, validation reports, and an assembly package
   for any service-installed SMD (BOM and placement/centroid data in the
   service's accepted format). Include the self-assembly BOM and drawings for
   through-hole parts. Do not treat generated files as permission to upload or
   order.
5. Use **PCBWay as the initial target service**. Capture its current accepted
   file formats, layer/process limits, panelization/outline rules, SMD assembly
   constraints, and sourcing requirements; recheck them at release rather than
   relying on remembered limits.
6. Capture known constraints and unresolved decisions in one issue/checklist
   with an owner and due point. Keep the notes in the project rather than
   relying on chat history.

### Baseline facts confirmed

- Installed KiCad CLI version: **10.0.8**.
- Authoritative working electrical source: `6502-electrical-draft.kicad_sch`,
  with companion project `6502-electrical-draft.kicad_pro`. The
  `6502-board.kicad_sch` file is the conceptual diagram, not the board-layout
  source.
- Local symbols are in `6502-board-local.kicad_sym`, registered by
  `sym-lib-table`. `generate_electrical_draft.py` is the schematic generator;
  it reads the local library and assumes KiCad 10's standard symbols are at
  `C:\Program Files\KiCad\10.0\share\kicad\symbols`.
- Tracked design exports include `6502-electrical-draft.csv` and
  `6502-electrical-draft.pdf`. The local `.kicad_prl` is editor/session state,
  not a tracked project input.
- The current CSV contains 49 BOM rows, all with assigned through-hole
  footprints and no SMD footprints. Thus the SMD assembly branch is presently
  a contingency, not an active assembly list; confirm after schematic parts
  are finalized.
- KiCad 10.0.8 ERC is documented as reporting zero violations. Netlist
  inspection is documented, but the CLI exporter emits an annotation warning.
  The checked-in documentation does not record the exact commands used for
  the previous ERC, netlist, PDF, or CSV exports. The following KiCad CLI
  command forms were verified on this machine; use a clean, designated reports
  directory for persistent reports:

  ```powershell
  & "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" sch erc --format report --output <erc-report> 6502-electrical-draft.kicad_sch
  & "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" sch export netlist --format kicadxml --output <netlist-file> 6502-electrical-draft.kicad_sch
  ```

  On 2026-11-05, ERC reported zero errors and warnings; the export commands
  returned success, while netlist export printed the documented annotation
  warning. The old PDF/CSV export invocations remain unknown and should be
  standardized when release automation is set up.
- The project owner selected **PCBWay** as the initial target and confirmed
  **free-size board outline**: no enclosure or maximum dimensions. Size the
  board for component/connector fit, usability, and practical routing. PCBWay's
  [published fabrication capabilities](https://www.pcbway.com/capabilities.html)
  provide process limits to consult, but the final stackup, upload format,
  outline rules, and SMD assembly/sourcing eligibility must be checked against
  the then-current service requirements once the design and any SMD BOM are
  known.
- The current BOM has no SMD footprints, so the current plan is fabrication
  only plus owner through-hole assembly. If any SMD parts are introduced, mark
  those exact items for service assembly and verify PCBWay eligibility; do not
  infer that every SMD component is covered by the assembly service.

### Phase 0 open-item register

| Open item | Owner | Due point |
|---|---|---|
| Resolve the KiCad netlist annotation warning in the schematic editor. | CAD implementer; hardware reviewer accepts the corrected schematic. | Before schematic freeze at Gate 2. |
| Record reproducible PDF and CSV/BOM export commands; preserve outputs outside local editor state. | CAD implementer. | During Phase 2 schematic normalization. |
| Confirm PCBWay stackup, outline, Gerber/drill upload, and fabrication constraints for the selected board option. | Project owner and CAD implementer. | Before locking board rules in Phase 5; recheck at Phase 9 release. |
| If SMD parts are added, confirm each part/package and BOM/placement format is eligible for PCBWay assembly. | Project owner and CAD implementer. | Before finalizing the assembly BOM in Phase 4; recheck at Phase 9. |

### Human guidance / approval gate

- The project owner has selected a PCBWay-targeted, service-uploadable
  Gerber/drill release and the hybrid assembly split: through-hole
  self-assembly, residual SMD service assembly where supported. The current
  BOM has no SMD parts. Confirm PCBWay's current requirements during layout and
  again before release.
- The project owner confirms that the existing socketed-DIP IC rule remains
  in force unless changed explicitly in the project requirements.
- The project owner confirms this deliverable is for their later upload; this
  task does not place an order or submit project files externally.

### Exit evidence

- A named source schematic, KiCad version, project/library files, and
  generator.
- Written deliverable: Gerbers and drill files plus editable KiCad sources and
  validation reports.
- Written assembly split and target service/process.
- Board outline is **free-size**: no fixed maximum or enclosure was specified.
  Size it around the components, connectors, usability, and practical routing;
  revisit only if a housing or other mechanical constraint is introduced.
- A list of open decisions with owners.

**Gate 0:** Do not start detailed board layout until the release target and
mechanical/fabrication inputs are known or explicitly marked as blocking.

## Phase 1 — Close component, power, and interface decisions

**Goal:** Replace provisional parts and undefined operating conditions with
verified, orderable design inputs.

### Work

1. **CPU, VIA, and logic**
   - Select exact orderable W65C02S and W65C22S variants, speed grades,
     packages, and operating conditions.
   - Verify their datasheet pinouts, supply ranges, input thresholds, output
     levels, bus timing, clock requirements, and reset/interrupt behavior.
   - Select exact 74HC-family parts (including manufacturer/variant) and verify
     pin mappings, VIH/VIL at the chosen supply, propagation delay, drive,
     operating range, and package.
2. **SRAM and bank hardware**
   - Resolve the stated 256 KiB logical SRAM requirement against the current
     512 KiB AS6C4008 candidate and its tied address pin.
   - Verify exact package, full address mapping, access/write timing, supply,
     pinout, decoupling, and ordering availability.
   - Verify bank-register reset, capture edge, mux behavior, and all 16 bank
     mappings, including intentional aliases.
3. **ROM**
   - Select an exact 3.3 V-compatible, socketed DIP ROM/EPROM orderable part;
     verify its capacity, read-only voltage, pinout, programming voltage and
     equipment, and current availability.
   - Check the 8 KiB image placement in the selected device, address-line ties,
     output-enable/select polarity, reset vector and interrupt vectors.
   - The existing candidate and its exact sourcing/programming support are
     explicitly unresolved in [DESIGN.md](./DESIGN.md). Do not layout it as a
     settled choice until this is closed.
4. **Power and reset**
   - Select the input supply arrangement and allowable input range. Calculate
     worst-case and startup current for every board load with datasheet
     conditions and margin.
   - Decide whether the board receives regulated 3.3 V or generates it. Verify
     regulator stability, thermal behavior, decoupling, reverse current, and
     connector polarity as applicable.
   - Define reset generation, reset duration/threshold, clock source and
     startup, and reset behavior of every bus-facing output.
   - Resolve independent Pico/main-board power and USB power sequencing.
     Specifically analyze back-power through the Pico GPIOs, the transceiver,
     and protection structures when either side is unpowered.
5. **Pico and bus interface**
   - Verify the Pico model/revision, harness pinout/orientation, common ground,
     GPIO availability and voltage limits.
   - Confirm U19 direction/OE polarity, passive reset defaults, direction
     truth table, bus ownership, ACK/REQ pulls, and reset during an in-flight
     transaction.
   - Verify the ROM’s VIA register configuration and four-phase handshake
     against the exact W65C22S datasheet. The existing emulator models are
     useful functional evidence, not proof of electrical timing.
6. **Mechanical and sourcing**
   - Confirm board outline/envelope, mounting holes, connector positions,
     Pico clearance and orientation, USB cable access, socket dimensions,
     component heights, and access for reset/debug/programming.
   - Confirm exact through-hole IC package widths and socket orderable parts.
     Add explicit sockets to the self-assembly BOM; a DIP footprint alone does not
     satisfy a socketed assembly requirement.

### Human guidance / approval gate

- The project owner supplies the supply source, use environment, mechanical
  envelope, and sourcing expectations; these cannot be safely inferred from
  the current schematic. The assembly split is specified as self-assembly for
  through-hole and service assembly for residual SMD; verify service capability
  and sourcing rules before finalizing parts.
- A hardware reviewer approves the exact part list and the voltage, current,
  timing, reset, and power-sequencing assumptions. In particular, do not waive
  the independently powered Pico/back-power question based only on schematic
  ERC.
- If an exact part cannot be sourced or does not meet the DIP/3.3 V constraints,
  the human owner decides whether to choose another part or revise the board
  requirements. Do not substitute silently.

### Exit evidence

- Approved component-selection table with orderable part, package, datasheet,
  footprint candidate, availability status, and design role.
- Power/current budget and documented reset, clock, and power-sequencing plan.
- Mechanical envelope and fabricator/assembler inputs.
- Closed or explicitly accepted interface and timing requirements.

**Gate 1:** No layout-ready schematic until all critical electrical and
mechanical choices are closed. “Accepted risk” must be explicit, reviewed, and
recorded; it is not equivalent to verified.

## Phase 2 — Normalize and complete the electrical schematic

**Goal:** Turn the existing electrical draft into a consistent, annotated
schematic suitable for PCB transfer.

### Work

1. Update symbols and fields to the selected exact parts, values, packages,
   datasheet links, and project references. Verify every pin number against the
   manufacturer datasheet, especially multi-unit logic symbols and power pins.
2. Review and document the full address decode and memory map:
   - fixed RAM, bank window, I/O, and ROM regions;
   - read/write qualification and bus-phase assumptions;
   - bank register write behavior, reset state, and aliases;
   - VIA decode, register mirror, and ROM vectors.
3. Review all supplies, grounds, power flags, bypass capacitors, bulk
   capacitance, reset, oscillator, pull-ups/pull-downs, and no-connects. Place
   each local bypass capacitor intentionally near the IC supply pins in the
   later layout.
4. Review the Pico harness as a real connector contract: pin number to Pico
   GPIO/signal, connector orientation, keying, ground, power exposure, and
   which side drives each signal. Verify labels and connector pin numbers
   against [pico/README.md](./pico/README.md).
5. Add or correct design intent notes for bus safe states, power sequencing,
   test points, and any approved exceptions. Avoid using the schematic as the
   only storage for unresolved design decisions.
6. Resolve the documented KiCad CLI annotation warning in the editor. Do not
   rely only on a generated netlist when the project’s own schematic identity
   warning remains unresolved.
7. Regenerate the netlist and re-check expected nets and representative
   connectivity: CPU-to-memory address/data/control, SRAM address mux, ROM
   selection and vectors, VIA bus, transceiver, Pico connector, power, ground,
   reset, and clock.

### Human guidance / review

- Review the schematic in the KiCad GUI at readable zoom; label-based
  connectivity is easy to misread in a PDF or raw netlist.
- Ask a second person to trace critical paths independently: reset-to-CPU,
  clock-to-CPU/VIA, CPU data bus to each memory/peripheral, bank-register
  writes, ROM select/read enable, and Pico-to-VIA handshake.
- Human reviewer signs off all intentional no-connects, ERC exclusions, and
  design-rule waivers. Do not suppress a warning just to make the report clean.

### Exit evidence

- Annotated, updated electrical schematic and regenerated netlist.
- Pin-by-pin verification record for all selected parts.
- ERC report with every warning/error resolved or individually justified and
  approved.
- Schematic review record with approved exceptions.

**Gate 2:** Freeze the schematic/netlist revision for layout. A later
connectivity change reopens schematic validation and requires PCB parity
recheck.

## Phase 3 — Validate electrical behavior and timing before placement

**Goal:** Make sure the intended circuit can meet its behavior at the selected
clock, supply, and component corners.

### Work

1. Create truth tables/timing sketches for memory selects, SRAM `/CE`, `/OE`,
   `/WE`, bank-register capture, ROM enable, VIA select, and bus transceiver
   direction/OE. Check legal and illegal cycles, including reset and
   simultaneous/control-transition cases.
2. Calculate CPU read/write timing budgets using the selected CPU speed grade,
   SRAM/ROM/VIA/logic delays, decoder paths, setup/hold requirements, and
   interconnect assumptions. Select the operating clock from the worst-case
   budget, not the provisional crystal value.
3. Verify power-up, brownout, reset assertion/release, and recovery after reset
   during a bus transaction. Include both power orders for Pico and main board.
4. Review the bus handshake as an electrical interface: data direction, output
   enable, setup/hold, ACK edge detection, passive defaults, and contention
   cases. Determine whether the implementation needs isolation, power-off
   tolerant buffers, or a sequencing requirement.
5. Exercise logic behavior with available simulation or a suitably bounded
   model. Extend ROM/Pico emulator tests for any changed memory map or contract.
   Clearly mark model limitations and do not treat them as physical proof.
6. Identify what must be verified on a prototype with an oscilloscope or logic
   analyzer: clock/reset waveforms, bus control timing, SRAM/ROM accesses,
   four-phase handshake, contention, power sequencing, and USB/Pico behavior.

### Human guidance / approval gate

- A qualified hardware reviewer checks calculations against the exact
  datasheets and selected clock/supply corners.
- A human must decide whether any physical measurement is required before
  board release. For this first board, treat measurements as required for
  claims about actual timing, reset recovery, and power sequencing; simulation
  and firmware tests alone cannot establish them.
- Do not connect or test hardware without confirming safe power limits and the
  bench setup. No physical test or programming is implied by this plan.

### Exit evidence

- Timing and logic review package with source datasheets and assumptions.
- Updated firmware/model tests for changed interface requirements.
- A list of required prototype measurements and pass criteria, approved by the
  hardware reviewer.

**Gate 3:** Do not proceed to layout release if contention, power-off behavior,
reset safety, or worst-case timing remains unbounded.

## Phase 4 — Build a verified symbol/footprint/BOM mapping

**Goal:** Ensure the PCB uses the physical parts actually approved in Phase 1.

### Work

1. Assign an exact footprint to every placed symbol, including connectors,
   crystals, capacitors, resistors, ICs, headers, switches, and test points.
2. Compare each footprint’s pad numbers and package dimensions to the chosen
   manufacturer drawing. Check pin 1, polarity, numbering convention,
   connector mating/orientation, hole sizes, annular rings, and socket fit.
3. Verify every IC socket footprint and add separate socket BOM line items
   (including width, pin count, and orderable part). Confirm the IC package
   fits the socket.
4. Inspect the Pico and harness geometry using the actual module dimensions,
   edge clearances, connector access, mounting method, and cable insertion
   direction.
5. Complete BOM fields: manufacturer, exact MPN, description, value, package,
   quantity, sourcing status, and whether the part is populated, optional, or
   a mechanical item. Separate or clearly flag the service-assembled SMD
   subset from the owner-installed through-hole subset; verify the service
   accepts every proposed SMD package and component.
6. Review special package requirements for the EPROM programmer, oscillator,
   regulator, and any parts with multiple package variants.

### Human guidance / review

- Compare critical footprints side-by-side with the datasheet’s recommended
  land pattern or mechanical drawing; AI/library checks should not be the sole
  dimensional review.
- The owner verifies that socket, IC, and connector combinations can actually
  be purchased and self-assembled, and that proposed SMD parts qualify for the
  selected service's assembly process.

### Exit evidence

- No unassigned footprints or unresolved pad-number mismatches.
- Datasheet-to-footprint review record for all ICs, connectors, and
  polarity-sensitive parts.
- Complete preliminary BOM including sockets and sourcing notes.

**Gate 4:** Do not create a “manufacturing” board from generic or guessed
footprints.

## Phase 5 — Define PCB constraints and create the board shell

**Goal:** Establish real manufacturing and mechanical constraints before
placing components.

### Work

1. Use PCBWay as the target and obtain its current stackup, minimum trace/space,
   via and drill limits, annular ring, solder-mask, copper, edge, slot, and
   assembly requirements. Also obtain its SMD assembly constraints and
   accepted BOM/placement formats if SMD assembly is needed. If a board option
   or assembly service is not yet selected, keep setup explicitly provisional
   and do not claim the Gerbers are upload-ready.
2. Select the number of copper layers and board material/stackup from signal,
   routing, cost, and return-path needs. Do not assume two layers without
   checking whether a continuous ground return and clean routing are practical.
3. Create KiCad board setup: layer stack, net classes, clearances, track/via
   dimensions, copper zones, mask/paste settings, and board-edge rules. Use
   values from the chosen fabricator and electrical review, not invented
   defaults.
4. Draw the board outline, mounting holes, keepouts, connector cutouts,
   component-height/USB clearances, and access areas from the approved
   mechanical envelope.
5. Establish net classes for power, ground, address/data/control buses, clocks,
   reset, and the Pico interface as appropriate. Record why each is assigned.
6. Import the frozen schematic into the `.kicad_pcb` and verify the full
   component count, netlist, footprint assignments, and unrouted connections.

### Human guidance / approval gate

- The project owner approves the board envelope and connector locations.
- The project owner confirms the selected service's current requirements
  before rules are treated as final. If no service is selected, keep the setup
  explicitly provisional and do not call the resulting files upload-ready.
- Human reviewer approves the layer count and board stackup because this
  affects return paths, signal quality, cost, and routing feasibility.

### Exit evidence

- Board shell with approved outline, holes, keepouts, layer stack, and net
  classes.
- A record of the source and date/version for fabrication constraints.
- Clean schematic-to-board component/net import.

**Gate 5:** No placement sign-off until the board outline and process rules are
agreed.

## Phase 6 — Place components and review the physical architecture

**Goal:** Produce a placement that supports electrical behavior, assembly,
debug, and maintenance.

### Work

1. Place edge-facing connectors first: power input, Pico harness, reset/debug,
   and any expansion connectors. Confirm cable, USB connector, and hand access.
2. Place the CPU, clock source, reset network, VIA, SRAM, ROM, bank register,
   decoder logic, transceiver, and bypass components by functional groups.
3. Keep clock/reset paths short and intentional. Put local decoupling at the
   relevant IC supply pins with a low-inductance return.
4. Place the SRAM/ROM and their decode logic to support short, direct address,
   data, and control paths. Keep the bank mux/register close to the SRAM
   address pins and related decode.
5. Group the VIA, transceiver, and Pico connector so bus directions are clear,
   data paths are compact, and the shared bus is easy to probe.
6. Reserve test points for supply/ground, reset, clock, CPU data/address or
   selected decode signals, bank-select outputs, VIA handshake lines, and
   transceiver enable/direction. Ensure probes can reach them after assembly.
7. Check socket extraction space, IC orientation markings, component labels,
   connector insertion, mechanical heights, and rework access.
8. Review power entry/regulation, ground return, and any separated noisy or
   externally connected signals.

### Human guidance / review

- Review placement in both 2D and 3D with the actual board outline and
  mechanical models where available. Confirm mating cables and Pico access
  manually.
- A human reviewer approves component orientation and the physical flow of
  the address/data/control buses before routing. This catches layout intent
  mistakes that DRC cannot detect.

### Exit evidence

- Annotated placement review and saved placement checkpoint.
- Verified connector and component clearances.
- Test-point and silkscreen plan.

**Gate 6:** Freeze placement before detailed routing; substantial movement
after routing begins requires rechecking affected nets and clearances.

## Phase 7 — Route, pour, and finish the PCB

**Goal:** Complete a clean, reviewable layout without compromising the agreed
electrical and manufacturing constraints.

### Work

1. Route critical signals first: clock, reset, CPU-to-memory timing paths,
   write enables/chip selects, bank select/capture, and VIA handshake.
2. Route the address and data buses with short, clear paths and avoid
   unnecessary stubs or loops. Keep transceiver-side and CPU-side ownership
   visually traceable.
3. Route power and ground with suitable current capacity and continuous return
   paths. Add copper zones and stitching vias based on the approved stackup.
   Avoid splitting the return path beneath critical signals.
4. Route remaining control and utility signals, keeping external connector
   signals, reset, and clock away from avoidable noise sources.
5. Place and inspect ground/power zones; verify thermal reliefs, clearances,
   isolated islands, stitching, and connections to the intended reference
   planes.
6. Add readable, assembly-oriented silkscreen: reference designators, pin 1,
   connector pin names/orientation, power polarity, test-point identities,
   board name/revision, and safety/voltage labels as appropriate.
7. Add board revision and manufacturing identifiers. Keep silkscreen off pads,
   holes, and critical markings.
8. Save incremental checkpoints or use version control to make routing changes
   reviewable and recoverable.

### Human guidance / review

- Human review is required for power/ground return paths, clock/reset routing,
  decoupling placement, connector polarity, and any signal crossing or plane
  split. A DRC cannot judge whether a return path is sensible.
- Do not add a blanket rule waiver to route faster. Resolve each violation
  locally or document its exact rationale and get reviewer approval.

### Exit evidence

- Fully routed board with no unreviewed unconnected items.
- Reviewed copper zones, return paths, critical net routing, and silkscreen.
- Saved board and project settings.

## Phase 8 — Run CAD checks and independent design reviews

**Goal:** Find both tool-detectable errors and human-visible design problems.

### Work

1. Run schematic ERC using the project’s KiCad version. Review every error,
   warning, exclusion, and unconnected pin; record approved exceptions.
2. Run PCB DRC using project/fabricator rules. Review unconnected items,
   clearances, board outline, mask/paste, holes, copper zones, silkscreen,
   courtyard/assembly overlaps, and all exclusions.
3. Run schematic-to-PCB parity checks. Compare component counts, reference
   designators, values, pad/net assignments, no-connects, and the generated
   netlist against the frozen schematic.
4. Inspect KiCad 3D render and fabrication plots. Check board outline, copper,
   drill, mask, silkscreen, connector position, socket orientation, and
   mechanical keepouts.
5. Use the installed `kicad-cli --help` and documentation for the installed
   KiCad version before scripting exports; do not assume CLI flags are stable.
6. Run firmware/emulator and Pico host tests again if board changes affect the
   memory map, register interface, GPIO allocation, reset contract, or
   protocol.
7. Ask a second reviewer to inspect the design from the schematic and the
   board independently, focusing on power, clock/reset, bus contention,
   address decode, ROM orientation/programming, Pico connection, and test
   access.

### Human guidance / approval gate

- The designer explains every ERC/DRC exclusion and design exception. The
  reviewer independently agrees before release.
- A clean report is necessary but not sufficient. Human reviewers must examine
  the rendered layers, mechanical fit, part suitability, power/timing analysis,
  and test strategy.
- Resolve the known CLI annotation warning documented in [DESIGN.md](./DESIGN.md)
  before considering the schematic package clean.

### Exit evidence

- Dated ERC, DRC, netlist/parity, and firmware test results.
- Reviewed schematic, PCB, 3D view, and plot set.
- Exception log with owner, rationale, and approval.

**Gate 8:** No design release with unexplained DRC/ERC issues, unresolved
connectivity differences, or unapproved exclusions.

## Phase 9 — Prepare and review the design release package

**Goal:** Make the design reproducible and prepare Gerber/drill files the owner
can upload to the chosen board service, with a separate assembly package for
residual SMD and instructions/BOM for owner-installed through-hole parts.

### Work

1. Freeze a revision identifier and archive the complete editable KiCad project,
   local libraries, board, schematic, and settings required to reproduce it.
2. Generate only the outputs required by the selected process, normally:
   - Gerber copper, solder-mask, silkscreen, and board-outline layers in the
     chosen service's currently accepted format;
   - plated/non-plated drill files and drill map;
   - fabrication notes and layer stack;
   - owner self-assembly BOM/drawings for through-hole parts, including the
     required IC sockets;
   - service-assembly BOM and placement/centroid data for only the residual
     SMD components, using the service's accepted format and part-sourcing
     rules;
   - board renders and validation reports.
3. Inspect the generated outputs independently of KiCad’s live editor. Verify
   layer naming, units, board outline closure, drill counts, plated status,
   copper polarity, mirrored/rotated placement, and expected board dimensions.
4. Reopen the release archive in a clean working directory and confirm it
   contains enough information to inspect or regenerate the design.
5. Record the exact KiCad version, export commands/settings, validation
   results, and remaining risks.

### Human guidance / approval gate

- The project owner and hardware reviewer approve the release archive. The
  owner performs and authorizes any upload or order; this plan and file
  generation do not submit anything externally.
- Before upload, the owner checks the service's current Gerber/drill preview,
  board outline, selected assembly options, component availability, BOM and
  placement interpretation. Do not treat successful file generation or an
  automated preview as manufacturing acceptance.

### Exit evidence

- Versioned release archive and checksum/manifest.
- Final reports and approval record.
- A clear status label such as “prototype design release — not yet
  hardware-validated,” unless later evidence justifies a stronger statement.

## Phase 10 — Prototype bring-up (after PCB design release)

This is the follow-on validation phase, not a prerequisite for creating the
PCB layout files. It is required before claiming that the design works on
physical hardware.

### Work

1. Human-inspect the assembled board for orientation, solder bridges, socket
   fit, shorts, and connector correctness before applying power.
2. Power the board under current-limited conditions using the approved
   bring-up procedure. Check rail voltage/current and reset/clock behavior
   before inserting or enabling optional modules as appropriate.
3. Bring up CPU, memory, ROM, bank register, and VIA in controlled stages.
   Verify expected address/data/control waveforms at the test points.
4. Test the Pico separately, then test both power sequences and the four-phase
   bus handshake with controlled firmware. Check for contention and reset
   during a transfer.
5. Program/install firmware only with explicit owner authorization. Verify
   ROM vectors and image identity before programming the selected device.
6. Run the monitor, memory/bank tests, loader, BASIC, USB terminal, and
   disconnect/reconnect/reset cases. Compare observed behavior with
   [firmware/PROTOCOL.md](./firmware/PROTOCOL.md).
7. Record measurements, failures, rework, and firmware/board revisions. Update
   schematic and PCB for every hardware change; re-run ERC, DRC, parity, and
   release checks.

### Human guidance / approval gate

- Physical power-up, programming, soldering, and measurements require explicit
  human authorization, an appropriate bench setup, and safe operating limits.
- A qualified reviewer evaluates unexpected current draw, heating, signal
  contention, or out-of-range waveforms. Stop rather than repeatedly
  power-cycling a board with an unexplained fault.

### Exit evidence

- Board revision and assembly record.
- Bench measurements and test outcomes with setup details.
- Remaining defects and next-revision decisions.

## Critical blockers at the start of this plan

Based on the project’s current documentation, treat these as blocking until
closed:

1. Exact, available, low-voltage socketed DIP ROM part and programming path.
2. Exact orderable CPU/VIA/SRAM/logic parts and datasheet-confirmed electrical
   and timing margins.
3. Complete 3.3 V source/current budget and safe reset, clock, and power-up
   behavior.
4. Safe Pico/main-board independent-power sequencing and power-off-tolerant
   bus behavior.
5. Board outline, connector/mechanical requirements, and fabrication/assembly
   rules.
6. Verified footprint and explicit socket BOM mapping for every main-board IC.
7. Resolution of the existing KiCad CLI annotation warning and approval of
   all schematic/ERC exceptions.

## Suggested immediate next actions

1. The project owner confirms board dimensions, power-input plan, and chosen
   target fabrication service. The assembly split is already set: self-assemble
   through-hole components; have the service install residual SMD components
   where it supports them.
2. The hardware reviewer selects or approves exact orderable parts, starting
   with the ROM, CPU/VIA, SRAM, and logic.
3. The designer prepares a component/power/timing decision record and closes
   the Phase 1 blockers.
4. After Gate 1, update and review the schematic; only then assign final
   footprints and create the PCB shell.

Do not begin detailed routing while Phase 1 blockers remain unresolved. It is
cheaper and safer to change the schematic and requirements before they become
copper.
