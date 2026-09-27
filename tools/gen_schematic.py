#!/usr/bin/env python3
"""Generate the project symbol library, sym-lib-table and the schematic.

Run from anywhere:  python3 tools/gen_schematic.py
"""
import json
import math
import os
import uuid

from design import COMPONENTS, PROJECT, TITLE, REV, POWER_NETS, NOT_IN_BOM, DNP
from sexpr import QStr as Q, parse, dump, find, find_all

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KICAD_SYM = '/usr/share/kicad/symbols'
NS = uuid.UUID('6f1c1d52-4c1e-4f0b-9d3e-3f6b1a9e0d11')


def uid(*parts):
    """Deterministic UUIDs so regenerating keeps schematic<->PCB links."""
    return str(uuid.uuid5(NS, '/'.join(parts)))


def font(size=1.27):
    return ['font', ['size', size, size]]


def effects(justify=None, hide=False, size=1.27):
    e = ['effects', font(size)]
    if justify:
        e.append(['justify'] + justify.split())
    if hide:
        e.append(['hide', 'yes'])
    return e


# ---------------------------------------------------------------- symbol lib
def lsm6dsv32x_symbol(name='LSM6DSV32X'):
    def pin(typ, num, pname, x, y, ang):
        return ['pin', typ, 'line', ['at', x, y, ang], ['length', 2.54],
                ['name', Q(pname), effects()], ['number', Q(num), effects()]]

    pins = [
        pin('input', '12', 'CS', -17.78, 5.08, 0),
        pin('input', '13', 'SCL/SPC', -17.78, 2.54, 0),
        pin('bidirectional', '14', 'SDA/SDI', -17.78, 0, 0),
        pin('bidirectional', '1', 'SDO/SA0', -17.78, -2.54, 0),
        pin('passive', '2', 'SDx/AH1', -17.78, -7.62, 0),
        pin('passive', '3', 'SCx/AH2', -17.78, -10.16, 0),
        pin('output', '4', 'INT1', 17.78, 5.08, 180),
        pin('output', '9', 'INT2', 17.78, 2.54, 180),
        pin('passive', '10', 'OCS_Aux', 17.78, -7.62, 180),
        pin('passive', '11', 'SDO_Aux', 17.78, -10.16, 180),
        pin('power_in', '8', 'VDD', -5.08, 15.24, 270),
        pin('power_in', '5', 'VDDIO', 5.08, 15.24, 270),
        pin('power_in', '6', 'GND', -2.54, -15.24, 90),
        pin('power_in', '7', 'GND', 2.54, -15.24, 90),
    ]

    def prop(k, v, x, y, justify=None, hide=False):
        return ['property', Q(k), Q(v), ['at', x, y, 0], effects(justify, hide)]

    return ['symbol', Q(name),
            ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'],
            prop('Reference', 'U', -15.24, 13.97, 'left'),
            prop('Value', name, 6.35, 13.97, 'left'),
            prop('Footprint', 'Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y',
                 0, -17.78, hide=True),
            prop('Datasheet', 'https://www.st.com/resource/en/datasheet/lsm6dsv32x.pdf',
                 0, -20.32, hide=True),
            prop('Description', '6-axis IMU, +-32g accelerometer, +-4000dps gyroscope, '
                 'I2C/I3C/SPI, 1.71V to 3.6V, LGA-14L 2.5x3mm', 0, 0, hide=True),
            prop('ki_keywords', 'IMU accelerometer gyroscope MEMS ST', 0, 0, hide=True),
            prop('ki_fp_filters', 'LGA*3x2.5mm*P0.5mm*LayoutBorder3x4y*', 0, 0, hide=True),
            ['symbol', Q(name + '_0_1'),
             ['rectangle', ['start', -15.24, 12.7], ['end', 15.24, -12.7],
              ['stroke', ['width', 0.254], ['type', 'default']],
              ['fill', ['type', 'background']]]],
            ['symbol', Q(name + '_1_1')] + pins]


def write_symbol_lib():
    lib = ['kicad_symbol_lib', ['version', 20241209], ['generator', Q('imuboard_gen')],
           ['generator_version', Q('9.0')], lsm6dsv32x_symbol()]
    with open(os.path.join(ROOT, 'imuboard.kicad_sym'), 'w') as f:
        f.write(dump(lib) + '\n')
    with open(os.path.join(ROOT, 'sym-lib-table'), 'w') as f:
        f.write('(sym_lib_table\n\t(version 7)\n')
        f.write('\t(lib (name "imuboard")(type "KiCad")(uri "${KIPRJMOD}/imuboard.kicad_sym")'
                '(options "")(descr "LSM6DSV32X breakout project symbols"))\n')
        # Stock libraries too, so the project resolves even without a global table.
        for lib in ('Device', 'power', 'Connector', 'Jumper'):
            f.write('\t(lib (name "%s")(type "KiCad")(uri "${KICAD9_SYMBOL_DIR}/%s.kicad_sym")'
                    '(options "")(descr "KiCad stock"))\n' % (lib, lib))
        f.write(')\n')


# ------------------------------------------------------------- lib symbols
_lib_cache = {}


def lib_symbol(lib_id):
    """Return a symbol definition renamed to 'Lib:Name' for lib_symbols."""
    lib, name = lib_id.split(':')
    if lib == 'imuboard':
        sym = lsm6dsv32x_symbol()
    else:
        if lib not in _lib_cache:
            with open(os.path.join(KICAD_SYM, lib + '.kicad_sym')) as f:
                _lib_cache[lib] = parse(f.read())
        sym = next(s for s in find_all(_lib_cache[lib], 'symbol') if s[1] == name)
        assert not find(sym, 'extends'), lib_id
    sym = list(sym)
    sym[1] = Q(lib_id)
    return sym


def sym_pins(sym):
    """{number: (x, y, angle)} in library coordinates (Y up)."""
    out = {}

    def walk(node):
        for x in node:
            if isinstance(x, list) and x:
                if x[0] == 'pin':
                    at = find(x, 'at')
                    out[str(find(x, 'number')[1])] = tuple(float(v) for v in at[1:4])
                else:
                    walk(x)
    walk(sym)
    return out


def xform(dx, dy, rot):
    """Library offset (Y up) -> schematic offset (Y down), rotated CCW by rot."""
    x, y = dx, -dy
    for _ in range(int(rot // 90) % 4):
        x, y = y, -x
    return x, y


def snap(v):
    return round(v / 1.27) * 1.27


# --------------------------------------------------------------- schematic
class Sheet:
    def __init__(self):
        self.root_uuid = uid('root')
        self.items = []
        self.lib_ids = {}
        self.pwr_count = 0
        self.symbol_uuids = {}

    def add_lib(self, lib_id):
        if lib_id not in self.lib_ids:
            self.lib_ids[lib_id] = lib_symbol(lib_id)
        return self.lib_ids[lib_id]

    def symbol(self, lib_id, ref, value, x, y, rot=0, footprint='', fields=None,
               hide_ref=False, in_bom=True, value_at=None, dnp=False):
        sym = self.add_lib(lib_id)
        u = uid('sym', ref)
        self.symbol_uuids[ref] = u
        node = ['symbol', ['lib_id', Q(lib_id)], ['at', x, y, rot], ['unit', 1],
                ['exclude_from_sim', 'no'], ['in_bom', 'yes' if in_bom else 'no'],
                ['on_board', 'yes' if in_bom or not ref.startswith('#') else 'no'],
                ['dnp', 'yes' if dnp else 'no'],
                ['fields_autoplaced', 'yes'], ['uuid', Q(u)]]
        libprops = {p[1]: p for p in find_all(sym, 'property')}

        def place(key, val, hide):
            lp = libprops.get(key)
            if lp is None:
                node.append(['property', Q(key), Q(val), ['at', x, y, 0], effects(None, True)])
                return
            at = find(lp, 'at')
            ang = float(at[3]) if len(at) > 3 else 0
            if key == 'Value' and value_at:
                (vx, vy), j = value_at
                node.append(['property', Q(key), Q(val), ['at', vx, vy, (360 - rot) % 360],
                             effects(j, hide)])
                return
            ox, oy = xform(float(at[1]), float(at[2]), rot)
            just = find(find(lp, 'effects'), 'justify')
            j = ' '.join(just[1:]) if just else None
            node.append(['property', Q(key), Q(val), ['at', x + ox, y + oy, ang],
                         effects(j, hide)])

        place('Reference', ref, hide_ref)
        place('Value', value, False)
        place('Footprint', footprint, True)
        ds = libprops.get('Datasheet')
        place('Datasheet', ds[2] if ds else '', True)
        place('Description', libprops['Description'][2] if 'Description' in libprops else '', True)
        for k, v in (fields or {}).items():
            node.append(['property', Q(k), Q(v), ['at', x, y, 0], effects(None, True)])
        for num in sym_pins(sym):
            node.append(['pin', Q(num), ['uuid', Q(uid('pin', ref, num))]])
        node.append(['instances', ['project', Q(PROJECT),
                                   ['path', Q('/' + self.root_uuid),
                                    ['reference', Q(ref)], ['unit', 1]]]])
        self.items.append(node)
        return sym

    def pin_geom(self, sym, pin, x, y, rot):
        px, py, pa = sym_pins(sym)[pin]
        ox, oy = xform(px, py, rot)
        ang = math.radians(pa + 180)       # outward direction, library coords
        dx, dy = xform(round(math.cos(ang)), round(math.sin(ang)), rot)
        return (snap(x + ox), snap(y + oy)), (dx, dy)

    def wire(self, a, b):
        self.items.append(['wire', ['pts', ['xy', a[0], a[1]], ['xy', b[0], b[1]]],
                           ['stroke', ['width', 0], ['type', 'default']],
                           ['uuid', Q(uid('wire', str(a), str(b)))]])

    def power(self, net, at, direction):
        """Power symbol whose graphic points along direction (dx, dy)."""
        self.pwr_count += 1
        ref = '#PWR%02d' % self.pwr_count
        if net == 'GND':
            rot = {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}[direction]
        else:
            rot = {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}[direction]
        value_at = None
        if direction[1] == 0:
            value_at = ((at[0] + 3.3 * direction[0], at[1] + 0.4),
                        'left' if direction[0] > 0 else 'right')
        self.symbol('power:' + net, ref, net, at[0], at[1], rot, hide_ref=True,
                    in_bom=False, value_at=value_at)

    def flag(self, net, at):
        self.pwr_count += 1
        ref = '#FLG%02d' % self.pwr_count
        rot = 180 if net == '+3V3' else 0
        self.symbol('power:PWR_FLAG', ref, 'PWR_FLAG', at[0], at[1], rot,
                    hide_ref=True, in_bom=False)

    def label(self, net, at, direction):
        ang, just = {(1, 0): (0, 'left bottom'), (-1, 0): (180, 'right bottom'),
                     (0, -1): (90, 'left bottom'), (0, 1): (270, 'right bottom')}[direction]
        self.items.append(['label', Q(net), ['at', at[0], at[1], ang],
                           ['fields_autoplaced', 'yes'], effects(just),
                           ['uuid', Q(uid('label', net, str(at)))]])

    def no_connect(self, at):
        self.items.append(['no_connect', ['at', at[0], at[1]],
                           ['uuid', Q(uid('nc', str(at)))]])

    def text(self, s, x, y, size=1.27):
        self.items.append(['text', Q(s), ['exclude_from_sim', 'no'], ['at', x, y, 0],
                           effects('left top', size=size), ['uuid', Q(uid('text', s))]])

    def place_part(self, ref, x, y, rot=0, stub=2.54, stubs=None):
        lib_id, value, fp, pins, fields = COMPONENTS[ref]
        sym = self.symbol(lib_id, ref, value, x, y, rot, fp, fields,
                          in_bom=ref not in NOT_IN_BOM, dnp=ref in DNP)
        for pin, net in pins.items():
            end, d = self.pin_geom(sym, pin, x, y, rot)
            if net is None:
                self.no_connect(end)
                continue
            L = (stubs or {}).get(net, stub)
            tip = (snap(end[0] + d[0] * L), snap(end[1] + d[1] * L))
            if L:
                self.wire(end, tip)
            if net in POWER_NETS:
                self.power(net, tip, d)
            else:
                self.label(net, tip, d)

    def write(self, path):
        sch = ['kicad_sch', ['version', 20250114], ['generator', Q('eeschema')],
               ['generator_version', Q('9.0')], ['uuid', Q(self.root_uuid)],
               ['paper', Q('A4')],
               ['title_block', ['title', Q(TITLE)], ['rev', Q(REV)],
                ['comment', 1, Q('Single-sided 2-layer, 0402 passives, header fitted from below')],
                ['comment', 2, Q('Per LSM6DSV32X datasheet DS13511, Fig. 28 (mode 1 connections)')]],
               ['lib_symbols'] + list(self.lib_ids.values())]
        sch += self.items
        sch += [['sheet_instances', ['path', Q('/'), ['page', Q('1')]]],
                ['embedded_fonts', 'no']]
        with open(path, 'w') as f:
            f.write(dump(sch) + '\n')


def main():
    write_symbol_lib()
    s = Sheet()
    g = 2.54
    s.place_part('J1', 20 * g, 36 * g, stubs={'+3V3': 4 * g, 'GND': 4 * g})
    s.place_part('U1', 44 * g, 36 * g)
    s.place_part('C1', 58 * g, 36 * g, stub=0)
    s.place_part('C2', 62 * g, 36 * g, stub=0)
    s.place_part('C3', 66 * g, 36 * g, stub=0)
    s.place_part('R3', 72 * g, 36 * g, stub=0)
    s.place_part('JP1', 58 * g, 50 * g, stub=g)
    s.place_part('R1', 66 * g, 50 * g, stub=0)
    s.place_part('R2', 70 * g, 50 * g, stub=0)

    # PWR_FLAGs: flag -- short wire -- power symbol.
    for i, net in enumerate(('+3V3', 'GND')):
        fx, fy = (20 + 6 * i) * g, 58 * g
        s.flag(net, (fx, fy))
        other = (fx, fy - g) if net == '+3V3' else (fx, fy + g)
        s.wire((fx, fy), other)
        s.power(net, other, (0, -1) if net == '+3V3' else (0, 1))

    s.text('Notes:\n'
           '- 3.3 V only: VDD and VDDIO are tied together (no regulator / level shifter).\n'
           '- I2C address 0x6B: SA0 pulled up by R3. Drive SDO low from the header for 0x6A.\n'
           '- CS has an internal pull-up, so the part starts in I2C/I3C mode; pull CS low for SPI.\n'
           '- JP1 (bridged by default) enables the 10k SCL/SDA pull-ups. Cut it to remove them.\n'
           '- SDx/SCx tied to GND (analog hub / Qvar / sensor hub not used), OCS_Aux/SDO_Aux left open\n'
           '  per datasheet Table 2 / Figure 28.\n'
           '- C3 (4.7uF) is DNP: optional bulk capacitor for noisy or long 3.3 V wiring.', 30 * g, 64 * g)
    s.text('SPI: SCL=SPC, SDA=SDI, SDO=SDO, CS=nCS', 40 * g, 24 * g)

    s.write(os.path.join(ROOT, PROJECT + '.kicad_sch'))
    with open(os.path.join(ROOT, 'tools', 'symbol_uuids.json'), 'w') as f:
        json.dump({'root': s.root_uuid, 'symbols': s.symbol_uuids}, f, indent=1)
    print('wrote', PROJECT + '.kicad_sch')


if __name__ == '__main__':
    main()
