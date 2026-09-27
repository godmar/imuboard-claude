"""Single source of truth for the LSM6DSV32X breakout netlist.

Both gen_schematic.py and gen_pcb.py import this, so the schematic and the
board always agree.
"""

PROJECT = 'lsm6dsv32x_breakout'
TITLE = 'LSM6DSV32X Breakout'
REV = '1.0'

# Header pin order (left to right, pin 1 = square pad).  The order follows the
# IMU pad ring so every signal routes on the top layer without crossings.
HEADER = ['+3V3', 'GND', 'INT2', 'CS', 'SCL', 'SDA', 'SDO', 'INT1']

# ref: (lib_id, value, footprint, {pin: net}, extra fields)
COMPONENTS = {
    'U1': ('imuboard:LSM6DSV32X', 'LSM6DSV32X',
           'Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y',
           {'1': 'SDO', '2': 'GND', '3': 'GND', '4': 'INT1', '5': '+3V3',
            '6': 'GND', '7': 'GND', '8': '+3V3', '9': 'INT2', '10': None,
            '11': None, '12': 'CS', '13': 'SCL', '14': 'SDA'},
           {'MPN': 'LSM6DSV32XTR'}),
    'C1': ('Device:C', '100nF', 'Capacitor_SMD:C_0402_1005Metric',
           {'1': '+3V3', '2': 'GND'}, {'Note': 'Vdd_IO decoupling'}),
    'C2': ('Device:C', '100nF', 'Capacitor_SMD:C_0402_1005Metric',
           {'1': '+3V3', '2': 'GND'}, {'Note': 'Vdd decoupling'}),
    'C3': ('Device:C', '4.7uF', 'Capacitor_SMD:C_0402_1005Metric',
           {'1': '+3V3', '2': 'GND'},
           {'Note': 'optional bulk for noisy/long supply wiring, X5R 6.3V+'}),
    'R1': ('Device:R', '10k', 'Resistor_SMD:R_0402_1005Metric',
           {'1': 'I2C_PU', '2': 'SCL'}, {}),
    'R2': ('Device:R', '10k', 'Resistor_SMD:R_0402_1005Metric',
           {'1': 'I2C_PU', '2': 'SDA'}, {}),
    'R3': ('Device:R', '10k', 'Resistor_SMD:R_0402_1005Metric',
           {'1': '+3V3', '2': 'SDO'}, {'Note': 'SA0=1 -> I2C addr 0x6B'}),
    'JP1': ('Jumper:SolderJumper_2_Bridged', 'I2C_PU',
            'Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm',
            {'1': '+3V3', '2': 'I2C_PU'}, {}),
    'J1': ('Connector:Conn_01x08_Pin', 'Conn_01x08',
           'Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical',
           {str(i + 1): n for i, n in enumerate(HEADER)}, {}),
}

POWER_NETS = ('+3V3', 'GND')

# Solder jumpers are copper only, not purchased parts.
NOT_IN_BOM = {'JP1'}

# Footprint present but not populated by default.
DNP = {}


def nets():
    out = {}
    for ref, (_, _, _, pins, _) in COMPONENTS.items():
        for pin, net in pins.items():
            if net:
                out.setdefault(net, []).append((ref, pin))
    return out
