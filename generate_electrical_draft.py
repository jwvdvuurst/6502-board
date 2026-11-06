from pathlib import Path
import re
import uuid


ROOT = Path(__file__).resolve().parent
LIB_PATH = ROOT / "6502-board-local.kicad_sym"
OUTPUT = ROOT / "6502-electrical-draft.kicad_sch"
LIB_TEXT = LIB_PATH.read_text(encoding="utf-8")
KICAD_SYMBOLS = Path(r"C:\Program Files\KiCad\10.0\share\kicad\symbols")


def new_uuid():
    return str(uuid.uuid4())


def balanced_block(text, start):
    depth = 0
    quoted = escaped = False
    for end, char in enumerate(text[start:], start):
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start : end + 1]
    raise ValueError("Unbalanced KiCad symbol block")


def symbol_data(name, text=None):
    if text is None:
        text = LIB_TEXT
    match = re.search(r'\(symbol "' + re.escape(name) + r'"', text)
    if not match:
        raise ValueError(f"Symbol not found: {name}")
    block = balanced_block(text, match.start())
    pins = []
    for match in re.finditer(r"\(pin\s+", block):
        pin = balanced_block(block, match.start())
        at = re.search(
            r"\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)", pin
        )
        name_match = re.search(r'\(name\s+"([^"]*)"', pin)
        number = re.search(r'\(number\s+"([^"]+)"', pin)
        if at and name_match and number:
            pin_name = name_match.group(1) or f"PIN{number.group(1)}"
            pins.append(
                (
                    number.group(1),
                    pin_name,
                    float(at.group(1)),
                    float(at.group(2)),
                    float(at.group(3)),
                )
            )
    return block, pins


def symbol_unit_data(name, unit, text=None):
    block, _ = symbol_data(name, text)
    unit_matches = list(
        re.finditer(
            r'\(symbol "' + re.escape(name) + rf'_{unit}_(\d+)"',
            block,
        )
    )
    if not unit_matches:
        raise ValueError(f"Symbol unit not found: {name} unit {unit}")
    unit_match = next(
        (
            match
            for match in unit_matches
            if match.group(1) == "1"
            and "(pin " in balanced_block(block, match.start())
        ),
        next(
            (
                match
                for match in unit_matches
                if "(pin " in balanced_block(block, match.start())
            ),
            unit_matches[0],
        ),
    )
    unit_block = balanced_block(block, unit_match.start())
    pins = []
    for match in re.finditer(r"\(pin\s+", unit_block):
        pin = balanced_block(unit_block, match.start())
        at = re.search(
            r"\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)", pin
        )
        name_match = re.search(r'\(name\s+"([^"]*)"', pin)
        number = re.search(r'\(number\s+"([^"]+)"', pin)
        if at and name_match and number:
            pin_name = name_match.group(1) or f"PIN{number.group(1)}"
            pins.append(
                (
                    number.group(1),
                    pin_name,
                    float(at.group(1)),
                    float(at.group(2)),
                    float(at.group(3)),
                )
            )
    return pins


def import_symbol(library_file, source_name, local_name):
    source_text = library_file.read_text(encoding="utf-8")
    match = re.search(r'\(symbol "' + re.escape(source_name) + r'"', source_text)
    if not match:
        raise ValueError(f"Symbol not found in {library_file}: {source_name}")
    block = balanced_block(source_text, match.start())
    block = block.replace(f'(symbol "{source_name}"', f'(symbol "{local_name}"', 1)
    block = block.replace(f'"{source_name}_', f'"{local_name}_')
    return block


def import_standard_symbol(library_name, source_name):
    source_path = KICAD_SYMBOLS / f"{library_name}.kicad_sym"
    source_text = source_path.read_text(encoding="utf-8")
    match = re.search(
        r'\(symbol "' + re.escape(source_name) + r'"', source_text
    )
    if not match:
        raise ValueError(f"Symbol not found in {source_path}: {source_name}")
    block = balanced_block(source_text, match.start())
    return block.replace(
        f'(symbol "{source_name}"',
        f'(symbol "{library_name}:{source_name}"',
        1,
    )


def install_local_symbols(symbols):
    global LIB_TEXT
    obsolete_symbols = {
        "74HC04",
        "74LVC1G00",
        "74LVC1G02",
        "74LVC1G04",
        "74LVC1G08",
        "74LVC1G10",
        "74LVC1G27",
    }
    for name in set(symbols) | obsolete_symbols:
        pattern = re.compile(
            r'(?m)^[ \t]*\(symbol "' + re.escape(name) + r'"(?=[ \t\n])'
        )
        match = pattern.search(LIB_TEXT)
        while match:
            old_block = balanced_block(LIB_TEXT, match.start())
            end = match.start() + len(old_block)
            LIB_TEXT = LIB_TEXT[: match.start()] + LIB_TEXT[end:]
            match = pattern.search(LIB_TEXT)
    LIB_TEXT = LIB_TEXT.rstrip()
    LIB_TEXT = LIB_TEXT[:-1] + "\n" + "\n".join(symbols.values()) + "\n)\n"
    LIB_PATH.write_text(LIB_TEXT, encoding="utf-8")


def symbol_instance(
    name,
    reference,
    value,
    x,
    y,
    pins,
    root_uuid,
    datasheet,
    footprint="Package_DIP:DIP-40_W15.24mm_Socket",
    label_offset=42,
    unit=1,
    show_reference=True,
    show_value=True,
    library_id="6502-board-local",
    in_bom=True,
    on_board=True,
    function=None,
):
    instance_uuid = new_uuid()
    lines = [
        f'  (symbol (lib_id "{library_id}:{name}") (at {x:.4f} {y:.4f} 0) (unit {unit})',
        f"    (exclude_from_sim no) (in_bom {'yes' if in_bom else 'no'}) (on_board {'yes' if on_board else 'no'}) (dnp no)",
        f'    (uuid "{instance_uuid}")',
        f'    (property "Reference" "{reference}" (at {x:.4f} {y - label_offset:.4f} 0) (effects (font (size 1.27 1.27)){"" if show_reference else " (hide yes)"}))',
        f'    (property "Value" "{value}" (at {x:.4f} {y - label_offset + 2.54:.4f} 0) (effects (font (size 1.27 1.27)){"" if show_value else " (hide yes)"}))',
        f'    (property "Footprint" "{footprint}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
        f'    (property "Datasheet" "{datasheet}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
    ]
    if function is not None:
        lines.append(
            f'    (property "Function" "{function}" (at 0 0 0) '
            '(effects (font (size 1.27 1.27)) (hide yes)))'
        )
    for number, *_ in pins:
        lines.append(f'    (pin "{number}" (uuid "{new_uuid()}"))')
    lines.extend(
        [
            f'    (instances (project "6502-electrical-draft" (path "/{root_uuid}" (reference "{reference}") (unit {unit}))))',
            "  )",
        ]
    )
    return "\n".join(lines)


def cpu_net(name):
    return {
        "~{VP}": None,
        "RDY": "RDY_N",
        "PHI1O": None,
        "~{IRQ}": "IRQ_N",
        "~{ML}": None,
        "~{NMI}": "NMI_N",
        "SYNC": None,
        "VDD": "+3V3",
        "VSS": "GND",
        "~{RW}": "RWB",
        "BE": "BE",
        "PHI2": "PHI2_IN",
        "~{SO}": "SO_N",
        "PHI2O": "PHI2O",
        "~{RES}": "RESET_N",
    }.get(name, name)


def via_net(name):
    result = {
        "VSS": "GND",
        "VDD": "+3V3",
        "~{IRQ}": "IRQ_N",
        "~{RW}": "RWB",
        "~{CS2}": "GND",
        "CS1": "VIA_CS1",
        "PHI2": "PHI2O",
        "~{RES}": "RESET_N",
        "CA2": "BUS_REQ",
        "CB1": "BUS_ACK",
        "PA0": "BUS_DIR",
        "CA1": None,
        "CB2": None,
        **{f"PA{i}": None for i in range(1, 8)},
    }.get(name, name)
    if name.startswith("RS") and name[2:].isdigit():
        return "A" + name[2:]
    if name.startswith("PB") and name[2:].isdigit():
        return "BUS_D" + name[2:]
    return result


def wire_label(x, y, angle, name):
    # Pin coordinates in symbol libraries use a y-up axis; the sheet uses y-down.
    x2, y2 = x, y
    if angle == 0:
        x2 -= 2.54
    elif angle == 180:
        x2 += 2.54
    elif angle == 90:
        y2 -= 2.54
    else:
        y2 += 2.54
    return (
        f'  (wire (pts (xy {x:.4f} {y:.4f}) (xy {x2:.4f} {y2:.4f})) '
        f'(stroke (width 0) (type default)) (uuid "{new_uuid()}"))\n'
        f'  (label "{name}" (at {x2:.4f} {y2:.4f} 0) '
        f'(effects (font (size 1.0 1.0)) (justify left bottom)) (uuid "{new_uuid()}"))'
    )


def no_connect(x, y):
    return (
        f'  (no_connect (at {x:.4f} {y:.4f}) '
        f'(uuid "{new_uuid()}"))'
    )


def add_component(
    name,
    library_id,
    reference,
    value,
    x,
    y,
    footprint,
    datasheet,
    mapping,
    unit=1,
    label_offset=12,
    show_reference=True,
    show_value=True,
    in_bom=True,
    on_board=True,
):
    x = round(x / 1.27) * 1.27
    y = round(y / 1.27) * 1.27
    source_path = KICAD_SYMBOLS / f"{library_id}.kicad_sym"
    source_text = source_path.read_text(encoding="utf-8")
    pins = symbol_data(name, source_text)[1]
    parts.append(
        symbol_instance(
            name,
            reference,
            value,
            x,
            y,
            pins,
            root_uuid,
            datasheet,
            footprint,
            label_offset,
            unit,
            show_reference,
            show_value,
            library_id,
            in_bom,
            on_board,
        )
    )
    for number, _, pin_x, pin_y, angle in pins:
        if number not in mapping:
            continue
        net = mapping[number]
        pin_x += x
        pin_y = y - pin_y
        connections.append(
            no_connect(pin_x, pin_y)
            if net is None
            else wire_label(pin_x, pin_y, angle, net)
        )


memory_ram = import_symbol(
    KICAD_SYMBOLS / "Memory_RAM.kicad_sym",
    "AS6C4008-55PCN",
    "AS6C4008-55PCN",
)
decoder = import_symbol(
    KICAD_SYMBOLS / "74xx.kicad_sym", "74HC138", "74HC138"
)
mux = import_symbol(KICAD_SYMBOLS / "74xx.kicad_sym", "74LS157", "74HC157")
mux = mux.replace("74LS157", "74HC157").replace(
    "http://www.ti.com/lit/gpn/sn74hc157",
    "https://www.ti.com/lit/ds/symlink/sn74hc157.pdf",
)
bank_register = import_symbol(
    KICAD_SYMBOLS / "74xx.kicad_sym", "74LS273", "74HC273"
)
bank_register = bank_register.replace("74LS273", "74HC273").replace(
    "https://assets.nexperia.com/documents/data-sheet/74HC_HCT273.pdf",
    "https://www.ti.com/lit/ds/symlink/sn74hc273.pdf",
)
gate_symbols = {}
for hc_name, ls_name in (
    ("74HC00", "74LS00"),
    ("74HC02", "74LS02"),
    ("74HCU04", "74LS04"),
    ("74HC08", "74LS08"),
    ("74HC10", "74LS10"),
    ("74HC27", "74LS27"),
    ("74HC245", "74LS245"),
):
    gate_symbols[hc_name] = import_symbol(
        KICAD_SYMBOLS / "74xx.kicad_sym", ls_name, hc_name
    )
    gate_symbols[hc_name] = gate_symbols[hc_name].replace(ls_name, hc_name)
    gate_symbols[hc_name] = gate_symbols[hc_name].replace(
        ls_name.lower(), hc_name.lower()
    )
    gate_symbols[hc_name] = re.sub(
        r'"https?://[^"]+"',
        lambda match: (
            f'"https://www.ti.com/lit/ds/symlink/sn{hc_name.lower()}.pdf"'
            if "lit/gpn/" in match.group(0).lower()
            else match.group(0)
        ),
        gate_symbols[hc_name],
    )
    if hc_name == "74HC245":
        gate_symbols[hc_name] = gate_symbols[hc_name].replace(
            "http://www.ti.com/lit/gpn/sn74hc245",
            "https://www.ti.com/lit/ds/symlink/sn74hc245.pdf",
        )
standard_symbols = {
    "Device:C": import_standard_symbol("Device", "C"),
    "Device:R": import_standard_symbol("Device", "R"),
    "Device:Crystal": import_standard_symbol("Device", "Crystal"),
    "Switch:SW_Push": import_standard_symbol("Switch", "SW_Push"),
    "Connector_Generic:Conn_01x02": import_standard_symbol(
        "Connector_Generic", "Conn_01x02"
    ),
    "Connector_Generic:Conn_01x14": import_standard_symbol(
        "Connector_Generic", "Conn_01x14"
    ),
    "Memory_EPROM:27C256": import_standard_symbol(
        "Memory_EPROM", "27C256"
    ),
    "power:PWR_FLAG": import_standard_symbol("power", "PWR_FLAG"),
}
install_local_symbols(
    {
        "AS6C4008-55PCN": memory_ram,
        "74HC138": decoder,
        "74HC157": mux,
        "74HC273": bank_register,
        **gate_symbols,
    }
)

cpu_symbol, cpu_pins = symbol_data("W65C02SxxP")
via_symbol, via_pins = symbol_data("W65C22SxxP")
ram_symbol, ram_pins = symbol_data("AS6C4008-55PCN")
decoder_symbol, decoder_pins = symbol_data("74HC138")
mux_symbol, mux_pins = symbol_data("74HC157")
bank_register_symbol, bank_register_pins = symbol_data("74HC273")
cpu_symbol = cpu_symbol.replace(
    '(symbol "W65C02SxxP"', '(symbol "6502-board-local:W65C02SxxP"', 1
)
via_symbol = via_symbol.replace(
    '(symbol "W65C22SxxP"', '(symbol "6502-board-local:W65C22SxxP"', 1
)
ram_symbol = ram_symbol.replace(
    '(symbol "AS6C4008-55PCN"', '(symbol "6502-board-local:AS6C4008-55PCN"', 1
)
decoder_symbol = decoder_symbol.replace(
    '(symbol "74HC138"', '(symbol "6502-board-local:74HC138"', 1
)
mux_symbol = mux_symbol.replace(
    '(symbol "74HC157"', '(symbol "6502-board-local:74HC157"', 1
)
bank_register_symbol = bank_register_symbol.replace(
    '(symbol "74HC273"', '(symbol "6502-board-local:74HC273"', 1
)
logic_symbols = {
    name: symbol.replace(
        f'(symbol "{name}"', f'(symbol "6502-board-local:{name}"', 1
    )
    for name, symbol in gate_symbols.items()
}
root_uuid = new_uuid()
cpu_x, cpu_y = 63.5, 104.14
via_x, via_y = 184.15, 104.14
ram_x, ram_y = 266.7, 104.14
decoder_x, decoder_y = 340.36, 50.8
io_decoder_x, io_decoder_y = 388.62, 50.8
address_mux_x, address_mux_y = 340.36, 109.22
bank_mux_x, bank_mux_y = 340.36, 170.18
bank_reg_x, bank_reg_y = 266.7, 190.5
logic_x = 388.62

parts = [
    symbol_instance(
        "W65C02SxxP",
        "U1",
        "W65C02S6TPG-14",
        cpu_x,
        cpu_y,
        cpu_pins,
        root_uuid,
        "https://www.westerndesigncenter.com/wdc/documentation/w65c02s.pdf",
    ),
    symbol_instance(
        "W65C22SxxP",
        "U2",
        "W65C22S6TPG-14",
        via_x,
        via_y,
        via_pins,
        root_uuid,
        "https://www.westerndesigncenter.com/wdc/documentation/w65c22.pdf",
    ),
    symbol_instance(
        "AS6C4008-55PCN",
        "U3",
        "AS6C4008 (512K x 8; use lower 256K)",
        ram_x,
        ram_y,
        ram_pins,
        root_uuid,
        "https://www.alliancememory.com/wp-content/uploads/pdf/AS6C4008.pdf",
        "Package_DIP:DIP-32_W15.24mm_Socket",
        38,
    ),
    symbol_instance(
        "74HC138",
        "U4",
        "74HC138",
        decoder_x,
        decoder_y,
        decoder_pins,
        root_uuid,
        "https://www.ti.com/lit/ds/symlink/sn74hc138.pdf",
        "Package_DIP:DIP-16_W7.62mm_Socket",
        25,
    ),
    symbol_instance(
        "74HC157",
        "U5",
        "74HC157 - SRAM address mux",
        address_mux_x,
        address_mux_y,
        mux_pins,
        root_uuid,
        "https://www.ti.com/lit/ds/symlink/sn74hc157.pdf",
        "Package_DIP:DIP-16_W7.62mm_Socket",
        28,
    ),
    symbol_instance(
        "74HC157",
        "U6",
        "74HC157 - bank write data mux",
        bank_mux_x,
        bank_mux_y,
        mux_pins,
        root_uuid,
        "https://www.ti.com/lit/ds/symlink/sn74hc157.pdf",
        "Package_DIP:DIP-16_W7.62mm_Socket",
        28,
    ),
    symbol_instance(
        "74HC273",
        "U7",
        "74HC273 - bank register",
        bank_reg_x,
        bank_reg_y,
        bank_register_pins,
        root_uuid,
        "https://www.ti.com/lit/ds/symlink/sn74hc273.pdf",
        "Package_DIP:DIP-20_W7.62mm_Socket",
        30,
    ),
    symbol_instance(
        "74HC138",
        "U9",
        "74HC138 - low-address I/O decode",
        io_decoder_x,
        io_decoder_y,
        decoder_pins,
        root_uuid,
        "https://www.ti.com/lit/ds/symlink/sn74hc138.pdf",
        "Package_DIP:DIP-16_W7.62mm_Socket",
        25,
    ),
    symbol_instance(
        "74HC245",
        "U19",
        "SN74HC245N - Pico/VIA bus transceiver",
        500.38,
        165.1,
        symbol_data("74HC245")[1],
        root_uuid,
        "https://www.ti.com/lit/ds/symlink/sn74hc245.pdf",
        "Package_DIP:DIP-20_W7.62mm_Socket",
        24,
    ),
]

logic_units = [
    ("74HCU04", "U8", 1, logic_x, 88.9, "BANK_CLK inverter", {
        "PIN1": "PHI2O", "PIN2": "BANK_CLK",
    }),
    ("74HCU04", "U8", 2, logic_x, 99.06, "RWB inverter", {
        "PIN3": "RWB", "PIN4": "RWB_N",
    }),
    ("74HCU04", "U8", 3, 388.62, 304.8, "1 MHz crystal oscillator", {
        "PIN5": "OSC_IN", "PIN6": "OSC_DRV",
    }),
    ("74HCU04", "U8", 4, 388.62, 327.66, "PHI2 clock buffer", {
        "PIN9": "OSC_DRV", "PIN8": "PHI2_IN",
    }),
    ("74HC00", "U10", 1, logic_x, 115.57, "RAM range", {
        "PIN1": "A15", "PIN2": "A14", "PIN3": "RAM_SEL",
    }),
    ("74HC00", "U10", 2, logic_x, 127.0, "RAM /CE", {
        "PIN4": "RAM_SEL", "PIN5": "PHI2O", "PIN6": "RAM_CE_N",
    }),
    ("74HC10", "U12", 1, logic_x, 140.97, "RAM /OE", {
        "PIN1": "RAM_SEL", "PIN2": "PHI2O", "PIN13": "RWB", "PIN12": "RAM_OE_N",
    }),
    ("74HC10", "U12", 2, logic_x, 154.94, "RAM /WE", {
        "PIN3": "RAM_SEL", "PIN4": "PHI2O", "PIN5": "RWB_N", "PIN6": "RAM_WE_N",
    }),
    ("74HC02", "U15", 1, logic_x, 171.45, "bank-window select", {
        "PIN1": "BANK_SEL", "PIN2": "PAGE_4_N", "PIN3": "PAGE_5_N",
    }),
    ("74HC02", "U15", 2, logic_x, 182.88, "VIA address select", {
        "PIN4": "VIA_DECODE", "PIN5": "PAGE_6_N", "PIN6": "SUBPAGE_1_N",
    }),
    ("74HC27", "U16", 1, logic_x, 198.12, "bank-register write select", {
        "PIN1": "PAGE_6_N", "PIN2": "SUBPAGE_0_N", "PIN13": "RWB",
        "PIN12": "BANK_REG_WRITE",
    }),
    ("74HC08", "U18", 1, logic_x, 213.36, "VIA phase enable", {
        "PIN1": "VIA_DECODE", "PIN2": "PHI2O", "PIN3": "VIA_CS1",
    }),
]
logic_unused_units = [
    ("74HCU04", "U8", 5, 106.68, 30.48, {
        "PIN11": "PAGE_7_N", "PIN10": "ROM_SEL",
    }),
    ("74HCU04", "U8", 6, 129.54, 30.48, {"PIN13": "GND", "PIN12": None}),
    ("74HC00", "U10", 3, 152.4, 20.32, {"PIN8": None, "PIN9": "GND", "PIN10": "GND"}),
    ("74HC00", "U10", 4, 175.26, 20.32, {"PIN11": None, "PIN12": "GND", "PIN13": "GND"}),
    ("74HC10", "U12", 3, 198.12, 20.32, {
        "PIN8": "ROM_OE_N",
        "PIN9": "PHI2O",
        "PIN10": "RWB",
        "PIN11": "ROM_SEL",
    }),
    ("74HC02", "U15", 3, 220.98, 20.32, {"PIN8": "GND", "PIN9": "GND", "PIN10": None}),
    ("74HC02", "U15", 4, 243.84, 20.32, {"PIN11": "GND", "PIN12": "GND", "PIN13": None}),
    ("74HC27", "U16", 2, 266.7, 20.32, {"PIN3": "GND", "PIN4": "GND", "PIN5": "GND", "PIN6": None}),
    ("74HC27", "U16", 3, 289.56, 20.32, {"PIN8": None, "PIN9": "GND", "PIN10": "GND", "PIN11": "GND"}),
    ("74HC08", "U18", 2, 312.42, 20.32, {"PIN4": "GND", "PIN5": "GND", "PIN6": None}),
    ("74HC08", "U18", 3, 335.28, 20.32, {"PIN8": None, "PIN9": "GND", "PIN10": "GND"}),
    ("74HC08", "U18", 4, 358.14, 20.32, {"PIN11": None, "PIN12": "GND", "PIN13": "GND"}),
]
connections = []
logic_packages = {}
for name, reference, unit, x, y, function, mapping in logic_units:
    pins = symbol_unit_data(name, unit)
    if reference not in logic_packages:
        logic_packages[reference] = name
    parts.append(
        symbol_instance(
            name,
            reference,
            name,
            x,
            y,
            pins,
            root_uuid,
            f"https://www.ti.com/lit/ds/symlink/sn{name.lower()}.pdf",
            "Package_DIP:DIP-14_W7.62mm_Socket",
            12,
            unit,
            show_value=unit == 1,
            function=function,
        )
    )
    for _, pin_name, pin_x, pin_y, angle in pins:
        if pin_name not in mapping:
            continue
        net = mapping[pin_name]
        connections.append(
            no_connect(x + pin_x, y - pin_y)
            if net is None
            else wire_label(x + pin_x, y - pin_y, angle, net)
        )

for name, reference, unit, x, y, mapping in logic_unused_units:
    pins = symbol_unit_data(name, unit)
    parts.append(
        symbol_instance(
            name,
            reference,
            name,
            x,
            y,
            pins,
            root_uuid,
            f"https://www.ti.com/lit/ds/symlink/sn{name.lower()}.pdf",
            "Package_DIP:DIP-14_W7.62mm_Socket",
            1,
            unit,
            show_reference=False,
            show_value=False,
            function="unused gate",
        )
    )
    for _, pin_name, pin_x, pin_y, angle in pins:
        if pin_name not in mapping:
            continue
        net = mapping[pin_name]
        connections.append(
            no_connect(x + pin_x, y - pin_y)
            if net is None
            else wire_label(x + pin_x, y - pin_y, angle, net)
        )

power_units = {
    "74HC00": 5,
    "74HC02": 5,
    "74HCU04": 7,
    "74HC08": 5,
    "74HC10": 4,
    "74HC27": 4,
    "74HC245": 3,
}
for index, (reference, name) in enumerate(logic_packages.items()):
    unit = power_units[name]
    x, y = 406.4, 12.7 + index * 50.8
    pins = symbol_unit_data(name, unit)
    parts.append(
        symbol_instance(
            name,
            reference,
            name,
            x,
            y,
            pins,
            root_uuid,
            f"https://www.ti.com/lit/ds/symlink/sn{name.lower()}.pdf",
            "Package_DIP:DIP-14_W7.62mm_Socket",
            1,
            unit,
            show_reference=False,
            show_value=False,
            function="power",
        )
    )
    for _, pin_name, pin_x, pin_y, angle in pins:
        net = {"GND": "GND", "VCC": "+3V3"}.get(pin_name)
        if net is not None:
            connections.append(
                wire_label(x + pin_x, y - pin_y, angle, net)
            )

for reference, name, x, y, net in (
    ("R3", "RDY_N pull-up", 445.0, 130.0, "RDY_N"),
    ("R4", "NMI_N pull-up", 445.0, 142.7, "NMI_N"),
    ("R5", "BE pull-up", 445.0, 155.4, "BE"),
    ("R6", "SO_N pull-up", 445.0, 168.1, "SO_N"),
    ("R7", "RESET_N pull-up", 445.0, 180.8, "RESET_N"),
    ("R8", "IRQ_N pull-up", 445.0, 193.5, "IRQ_N"),
):
    add_component(
        "R", "Device", reference, f"10k - {name}", x, y,
        "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
        "", {"1": "+3V3", "2": net},
        label_offset=7.62,
    )

add_component(
    "R", "Device", "R1", "1M - HCU04 crystal feedback", 445.0, 304.8,
    "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    "", {"1": "OSC_DRV", "2": "OSC_IN"},
    label_offset=7.62,
)
add_component(
    "R", "Device", "R2", "1k - crystal drive limiter", 465.0, 304.8,
    "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    "", {"1": "OSC_DRV", "2": "OSC_NODE"},
    label_offset=7.62,
)
add_component(
    "C", "Device", "C1", "100nF - RESET_N power-on delay", 470.0, 180.8,
    "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "", {"1": "RESET_N", "2": "GND"},
    label_offset=7.62,
)
add_component(
    "C", "Device", "C2", "27pF - crystal load", 485.0, 304.8,
    "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "", {"1": "OSC_IN", "2": "GND"},
    label_offset=7.62,
)
add_component(
    "C", "Device", "C3", "27pF - crystal load", 500.0, 304.8,
    "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "", {"1": "OSC_NODE", "2": "GND"},
    label_offset=7.62,
)
add_component(
    "Crystal", "Device", "Y1", "1.000MHz fundamental, CL=16pF",
    475.0, 327.66,
    "Crystal:Crystal_HC49-U_Vertical",
    "", {"1": "OSC_IN", "2": "OSC_NODE"},
    label_offset=7.62,
)
add_component(
    "SW_Push", "Switch", "SW1", "RESET", 500.0, 180.8,
    "Button_Switch_THT:SW_PUSH_6mm",
    "", {"1": "RESET_N", "2": "GND"},
    label_offset=7.62,
)

add_component(
    "R", "Device", "R9", "10k - BUS_OE_N reset pull-up", 530.0, 205.0,
    "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    "", {"1": "+3V3", "2": "BUS_OE_N"},
    label_offset=7.62,
)
add_component(
    "R", "Device", "R10", "10k - BUS_REQ reset pull-down", 530.0, 217.7,
    "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    "", {"1": "GND", "2": "BUS_REQ"},
    label_offset=7.62,
)
add_component(
    "R", "Device", "R11", "10k - BUS_DIR reset pull-down", 530.0, 230.4,
    "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    "", {"1": "GND", "2": "BUS_DIR"},
    label_offset=7.62,
)
add_component(
    "R", "Device", "R12", "10k - BUS_ACK idle pull-down", 530.0, 243.1,
    "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    "", {"1": "GND", "2": "BUS_ACK"},
    label_offset=7.62,
)
add_component(
    "Conn_01x02", "Connector_Generic", "J1",
    "REGULATED +3V3 INPUT - no regulator on board", 465.0, 80.0,
    "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    "", {"1": "+3V3", "2": "GND"},
    label_offset=12.7,
)
add_component(
    "Conn_01x14", "Connector_Generic", "J2",
    "Pico external harness - do not power Pico from this header",
    540.0, 116.84,
    "Connector_PinHeader_2.54mm:PinHeader_1x14_P2.54mm_Vertical",
    "", {
        "1": "PICO_GP0",
        "2": "PICO_GP1",
        "3": "PICO_GP2",
        "4": "PICO_GP3",
        "5": "PICO_GP4",
        "6": "PICO_GP5",
        "7": "PICO_GP6",
        "8": "PICO_GP7",
        "9": "BUS_REQ",
        "10": "BUS_ACK",
        "11": "BUS_DIR",
        "12": "BUS_OE_N",
        "13": "GND",
        "14": "GND",
    },
    label_offset=25.4,
)
add_component(
    "27C256", "Memory_EPROM", "U20",
    "AT27LV256A 3.3V OTP EPROM - legacy DIP variant; verify sourcing",
    485.14, 53.34,
    "Package_DIP:DIP-28_W15.24mm_Socket",
    "https://ww1.microchip.com/downloads/en/DeviceDoc/doc0601.pdf",
    {
        "1": "+3V3",
        "2": "A12",
        "3": "A7",
        "4": "A6",
        "5": "A5",
        "6": "A4",
        "7": "A3",
        "8": "A2",
        "9": "A1",
        "10": "A0",
        "11": "D0",
        "12": "D1",
        "13": "D2",
        "14": "GND",
        "15": "D3",
        "16": "D4",
        "17": "D5",
        "18": "D6",
        "19": "D7",
        "20": "PAGE_7_N",
        "21": "A10",
        "22": "ROM_OE_N",
        "23": "A11",
        "24": "A9",
        "25": "A8",
        "26": "GND",
        "27": "GND",
        "28": "+3V3",
    },
    label_offset=30.48,
)
add_component(
    "PWR_FLAG", "power", "#FLG0101", "PWR_FLAG", 465.0, 96.52,
    "", "", {"1": "+3V3"},
    label_offset=1,
    show_reference=False,
    show_value=False,
    in_bom=False,
    on_board=False,
)
add_component(
    "PWR_FLAG", "power", "#FLG0102", "PWR_FLAG", 475.0, 96.52,
    "", "", {"1": "GND"},
    label_offset=1,
    show_reference=False,
    show_value=False,
    in_bom=False,
    on_board=False,
)

for index, (reference, name) in enumerate(
    (
        ("U1", "CPU"),
        ("U2", "VIA"),
        ("U3", "SRAM"),
        ("U4", "address decoder"),
        ("U5", "address mux"),
        ("U6", "bank data mux"),
        ("U7", "bank register"),
        ("U8", "oscillator and inverters"),
        ("U9", "I/O decoder"),
        ("U10", "NAND logic"),
        ("U12", "3-input NAND logic"),
        ("U15", "NOR logic"),
        ("U16", "3-input NOR logic"),
        ("U18", "AND logic"),
        ("U19", "bus transceiver"),
        ("U20", "EPROM"),
    )
):
    column, row = divmod(index, 5)
    add_component(
        "C", "Device", f"C{index + 4}", f"100nF - {reference} {name}",
        540.0 + column * 17.78, 195.58 + row * 17.78,
        "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
        "", {"1": "+3V3", "2": "GND"},
        label_offset=7.62,
    )
add_component(
    "C", "Device", "C20", "100nF - EPROM bypass", 510.54, 53.34,
    "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "", {"1": "+3V3", "2": "GND"},
    label_offset=7.62,
)
add_component(
    "C", "Device", "C21", "10uF - 3V3 bulk bypass", 465.0, 112.0,
    "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "", {"1": "+3V3", "2": "GND"},
    label_offset=7.62,
)

for pins, x0, y0, mapping in (
    (
        symbol_data("74HC245")[1],
        500.38,
        165.1,
        {
            "A->B": "BUS_DIR",
            "CE": "BUS_OE_N",
            **{f"A{i}": f"PICO_GP{i}" for i in range(8)},
            **{f"B{i}": f"BUS_D{i}" for i in range(8)},
            "GND": "GND",
            "VCC": "+3V3",
        },
    ),
    (cpu_pins, cpu_x, cpu_y, {name: cpu_net(name) for _, name, *_ in cpu_pins}),
    (via_pins, via_x, via_y, {name: via_net(name) for _, name, *_ in via_pins}),
    (
        ram_pins,
        ram_x,
        ram_y,
        {
            **{f"A{i}": f"A{i}" for i in range(14)},
            "A14": "SRAM_A14",
            "A15": "SRAM_A15",
            "A16": "SRAM_A16",
            "A17": "SRAM_A17",
            "A18": "GND",
            **{f"DQ{i}": f"D{i}" for i in range(8)},
            "VCC": "+3V3",
            "VSS": "GND",
            "CE#": "RAM_CE_N",
            "OE#": "RAM_OE_N",
            "WE#": "RAM_WE_N",
        },
    ),
    (
        decoder_pins,
        decoder_x,
        decoder_y,
        {
            "A0": "A13",
            "A1": "A14",
            "A2": "A15",
            "~{E0}": "GND",
            "~{E1}": "GND",
            "E2": "+3V3",
            **{
                f"~{{Y{i}}}": (
                    f"PAGE_{i}_N" if i in (4, 5, 6, 7) else None
                )
                for i in range(8)
            },
            "VCC": "+3V3",
            "GND": "GND",
        },
    ),
    (
        decoder_pins,
        io_decoder_x,
        io_decoder_y,
        {
            "A0": "A8",
            "A1": "A9",
            "A2": "A10",
            "~{E0}": "A12",
            "~{E1}": "A11",
            "E2": "+3V3",
            **{
                f"~{{Y{i}}}": (
                    f"SUBPAGE_{i}_N" if i in (0, 1) else None
                )
                for i in range(8)
            },
            "VCC": "+3V3",
            "GND": "GND",
        },
    ),
    (
        mux_pins,
        address_mux_x,
        address_mux_y,
        {
            "S": "BANK_SEL",
            "E": "GND",
            "I0a": "A14",
            "I1a": "BANK_Q0",
            "Za": "SRAM_A14",
            "I0b": "GND",
            "I1b": "BANK_Q1",
            "Zb": "SRAM_A15",
            "I0c": "GND",
            "I1c": "BANK_Q2",
            "Zc": "SRAM_A16",
            "I0d": "GND",
            "I1d": "BANK_Q3",
            "Zd": "SRAM_A17",
            "VCC": "+3V3",
            "GND": "GND",
        },
    ),
    (
        mux_pins,
        bank_mux_x,
        bank_mux_y,
        {
            "S": "BANK_REG_WRITE",
            "E": "GND",
            "I0a": "BANK_Q0",
            "I1a": "D0",
            "Za": "BANK_D0",
            "I0b": "BANK_Q1",
            "I1b": "D1",
            "Zb": "BANK_D1",
            "I0c": "BANK_Q2",
            "I1c": "D2",
            "Zc": "BANK_D2",
            "I0d": "BANK_Q3",
            "I1d": "D3",
            "Zd": "BANK_D3",
            "VCC": "+3V3",
            "GND": "GND",
        },
    ),
    (
        bank_register_pins,
        bank_reg_x,
        bank_reg_y,
        {
            "~{Mr}": "RESET_N",
            "Cp": "BANK_CLK",
            **{f"D{i}": f"BANK_D{i}" for i in range(4)},
            **{f"D{i}": "GND" for i in range(4, 8)},
            **{f"Q{i}": f"BANK_Q{i}" for i in range(4)},
            **{f"Q{i}": None for i in range(4, 8)},
            "GND": "GND",
            "VCC": "+3V3",
        },
    ),
):
    for _, pin_name, pin_x, pin_y, angle in pins:
        if pin_name not in mapping:
            continue
        x = x0 + pin_x
        y = y0 - pin_y
        net = mapping[pin_name]
        if net is None:
            connections.append(no_connect(x, y))
        else:
            connections.append(wire_label(x, y, angle, net))

sheet = f"""(kicad_sch
  (version 20260306)
  (generator "eeschema")
  (generator_version "10.0")
  (uuid "{root_uuid}")
  (paper "A2")
  (title_block
    (title "6502 Electrical Draft - CPU, VIA, SRAM and EPROM")
    (date "2026-11-04")
    (rev "0.2")
    (comment 1 "Socketed-DIP 3.3 V design draft; legacy OTP EPROM sourcing TBD")
    (comment 2 "NOT PCB-ready: verify timing, power, bus interface, BOM and mechanics")
  )
  (lib_symbols
{cpu_symbol}
{via_symbol}
{ram_symbol}
{decoder_symbol}
{mux_symbol}
{bank_register_symbol}
{chr(10).join(logic_symbols.values())}
{chr(10).join(standard_symbols.values())}
  )
  (embedded_fonts no)
{chr(10).join(parts)}
{chr(10).join(connections)}
  (text "HOW TO FOLLOW CONNECTIONS: each pin stub ends at a net label; identical labels are electrically connected. A0-A13: U1-U3; A0-A12 also U20. D0-D7: U1, U2, U3 and U20. Click a label in KiCad to highlight its full net." (exclude_from_sim no) (at 20 234 0) (effects (font (size 1.1 1.1)) (justify left bottom)) (uuid "{new_uuid()}"))
  (text "CPU/VIA: A0-A15, D0-D7, RWB, RESET_N, IRQ_N. CPU PHI2 is an input; PHI2O drives the VIA clock." (exclude_from_sim no) (at 20 240 0) (effects (font (size 1.1 1.1)) (justify left bottom)) (uuid "{new_uuid()}"))
  (text "SRAM: A0-A13 direct; U5 selects CPU A14 and fixed zeros or BANK_Q[3:0] for SRAM A14-A17. A18 is grounded, using half of this 512Kx8 candidate." (exclude_from_sim no) (at 20 246 0) (effects (font (size 1.1 1.1)) (justify left bottom)) (uuid "{new_uuid()}"))
  (text "U7 resets the bank to zero; U6 holds or loads D0-D3 when BANK_REG_WRITE is true. U8 inverts PHI2O and RWB." (exclude_from_sim no) (at 20 252 0) (effects (font (size 1.1 1.1)) (justify left bottom)) (uuid "{new_uuid()}"))
  (text "U4/U9 decode address pages. Socketed DIP U10/U12 generate RAM select and PHI2-qualified active-low CE/OE/WE; OE and WE are mutually exclusive." (exclude_from_sim no) (at 20 258 0) (effects (font (size 1.1 1.1)) (justify left bottom)) (uuid "{new_uuid()}"))
  (text "Socketed DIP U15-U16 and U18 generate bank-window select, qualified bank-register writes and PHI2-qualified VIA CS1; VIA CS2_N is tied low." (exclude_from_sim no) (at 20 264 0) (effects (font (size 1.1 1.1)) (justify left bottom)) (uuid "{new_uuid()}"))
  (text "Text screen: reserve SRAM $7800-$7FFF as a 25x80 row-major character buffer; ROM sends it to the Pico through the VIA. No character ROM or video hardware." (exclude_from_sim no) (at 20 270 0) (effects (font (size 1.1 1.1)) (justify left bottom)) (uuid "{new_uuid()}"))
  (text "Power: J1 accepts externally regulated +3V3 only; no regulator is fitted. C21 is bulk bypass; C4-C19 are IC bypass capacitors." (exclude_from_sim no) (at 20 276 0) (effects (font (size 1.1 1.1)) (justify left bottom)) (uuid "{new_uuid()}"))
  (text "Clock: 1.000MHz crystal with socketed 74HCU04 Pierce oscillator, series drive resistor and buffer. Verify crystal startup and CPU clock limits on hardware." (exclude_from_sim no) (at 20 282 0) (effects (font (size 1.1 1.1)) (justify left bottom)) (uuid "{new_uuid()}"))
  (text "Reset: pull-up, 100nF power-on delay and pushbutton; CPU RDY/NMI/BE/SO and IRQ have defined pull-ups. Validate reset timing from the exact CPU datasheet." (exclude_from_sim no) (at 20 288 0) (effects (font (size 1.1 1.1)) (justify left bottom)) (uuid "{new_uuid()}"))
  (text "Pico is external: J2 pins 1-8 GP0-GP7, 9 REQ, 10 ACK, 11 DIR, 12 OE_N, 13-14 GND. Pico is separately USB-powered; provide common ground." (exclude_from_sim no) (at 20 294 0) (effects (font (size 1.1 1.1)) (justify left bottom)) (uuid "{new_uuid()}"))
  (text "U19 SN74HC245N routes Pico A0-A7 to VIA B0-B7; DIR=BUS_DIR, OE_N=BUS_OE_N. Bus direction/output-enable reset defaults are passive." (exclude_from_sim no) (at 20 300 0) (effects (font (size 1.1 1.1)) (justify left bottom)) (uuid "{new_uuid()}"))
  (text "U20 AT27LV256A: A0-A12 to CPU A0-A12; A13/A14 strapped low for an 8KiB image at $E000-$FFFF. /CE=PAGE_7_N; /OE=PHI2-qualified read." (exclude_from_sim no) (at 20 306 0) (effects (font (size 1.1 1.1)) (justify left bottom)) (uuid "{new_uuid()}"))
  (text "U20 is shown as a socketed DIP-28 3.3V OTP EPROM legacy candidate; confirm the genuine DIP orderable variant and availability before PCB. Program reset vector at $FFFC/$FFFD." (exclude_from_sim no) (at 20 312 0) (effects (font (size 1.1 1.1)) (justify left bottom)) (uuid "{new_uuid()}"))
  (text "NOT fabrication-ready: exact EPROM package/sourcing, oscillator and reset timing, power budget/sequencing, Pico harness, BOM and board mechanics need review." (exclude_from_sim no) (at 20 318 0) (effects (font (size 1.1 1.1)) (justify left bottom)) (uuid "{new_uuid()}"))
  (sheet_instances (path "/" (page "1")))
)
"""
OUTPUT.write_text(sheet, encoding="utf-8")
print(f"Wrote {OUTPUT}")
