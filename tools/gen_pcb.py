#!/usr/bin/env python3
"""Generate the LSM6DSV32X breakout PCB (placement, routing, pours, silk).

Needs KiCad's pcbnew Python module (system python3 on Linux):
    python3 tools/gen_schematic.py   # first, writes symbol_uuids.json
    python3 tools/gen_pcb.py

All coordinates below are mm relative to the board's top-left corner.
Board: 20.32 x 10.2 mm (JLCPCB assembly needs >= 10 x 10 mm), 2 layers, all
SMD parts on top, 1x8 2.54 mm header fitted from the bottom (plastic spacer
underneath, so it can't hit top parts), two M2 mounting holes along the top.

Circuit coordinates (PLACEMENT, VIAS, TRACKS) are relative to the circuit
area, which sits DY below the board's top edge; the band above it holds the
mounting holes.
"""
import json
import os

import pcbnew
from design import COMPONENTS, PROJECT, HEADER, POWER_NETS, DNP

NC_PIN_NAMES = {('U1', '10'): 'OCS_Aux', ('U1', '11'): 'SDO_Aux'}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPDIR = '/usr/share/kicad/footprints'
OX, OY = 100.0, 100.0            # board origin on the KiCad canvas
W, H = 20.32, 10.2                # board size
DY = 3.2                          # circuit area offset below the top edge
HY = H - 1.27                     # header row
CORNER_R = 0.5

mm = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def C(x, y):
    """Point in circuit-area coordinates."""
    return P(x, y + DY)


# ------------------------------------------------------------------ placement
PLACEMENT = {                     # ref: (x, y, rotation_deg)
    'U1': (11.43, 2.30, 180),     # rotated so CS/SCL/SDA face the header
    'C1': (14.20, 0.70, 0),       # Vdd_IO decoupling
    'C2': (8.60, 0.70, 180),      # Vdd decoupling
    'C3': (6.20, 0.70, 0),        # optional bulk
    'R3': (16.00, 2.30, 0),       # SDO/SA0 pull-up
    'JP1': (2.20, 2.90, 270),     # pull-up enable
    'R2': (4.40, 3.20, 0),        # SDA pull-up
    'R1': (4.40, 4.15, 0),        # SCL pull-up
}

HOLES = {'H1': (2.30, 1.90), 'H2': (W - 2.30, 1.90)}   # board coordinates

VIAS = [                          # net, x, y
    ('GND', 7.40, 0.70), ('GND', 13.40, 2.30), ('GND', 15.40, 0.70),
    ('+3V3', 12.40, 0.70), ('+3V3', 14.75, 2.30),
    ('SDA', 5.70, 3.20), ('SCL', 5.70, 4.15),
]

PWR, SIG, GNDW = 0.3, 0.2, 0.25
F, B = 'F.Cu', 'B.Cu'
# net, layer, width, points ('REF.PAD' = that pad's centre)
TRACKS = [
    ('+3V3', F, PWR, ['U1.5', (11.93, 0.70), 'C1.1']),
    ('+3V3', F, PWR, [(11.93, 0.70), (9.70, 0.70), (9.70, 1.55), 'U1.8']),
    ('+3V3', F, PWR, ['C2.1', (9.70, 0.70)]),
    ('+3V3', F, PWR, [(9.70, 1.55), (0.75, 1.55), (0.75, 5.00), 'J1.1']),
    ('+3V3', F, PWR, ['C3.1', (5.69, 1.55)]),
    ('+3V3', F, PWR, ['JP1.1', (2.20, 1.55)]),
    ('+3V3', F, PWR, ['R3.1', (14.75, 2.30)]),
    ('+3V3', B, PWR, [(12.40, 0.70), (14.75, 2.30)]),
    ('GND', F, SIG, ['U1.7', 'U1.6', (11.43, 2.05), 'U1.3', 'U1.2']),
    ('GND', F, GNDW, [(12.5925, 2.30), (13.40, 2.30)]),
    ('GND', F, GNDW, ['C2.2', (7.40, 0.70), 'C3.2']),
    ('GND', F, GNDW, ['C1.2', (15.40, 0.70)]),
    ('INT2', F, SIG, ['U1.9', (8.00, 2.05), (6.35, 3.70), 'J1.3']),
    ('CS', F, SIG, ['U1.12', (10.93, 3.75), (9.90, 3.75), (8.89, 4.76), 'J1.4']),
    ('SCL', F, SIG, ['U1.13', 'J1.5']),
    ('SDA', F, SIG, ['U1.14', (11.93, 3.75), (12.96, 3.75), (13.97, 4.76), 'J1.6']),
    ('SDO', F, SIG, ['U1.1', (16.51, 3.05), 'J1.7']),
    ('SDO', F, SIG, ['R3.2', (16.51, 3.05)]),
    ('INT1', F, SIG, ['U1.4', (18.50, 1.55), (19.05, 2.10), 'J1.8']),
    ('I2C_PU', F, SIG, ['JP1.2', (3.89, 3.55)]),
    ('I2C_PU', F, SIG, ['R2.1', 'R1.1']),
    ('SDA', F, SIG, ['R2.2', (5.70, 3.20)]),
    ('SCL', F, SIG, ['R1.2', (5.70, 4.15)]),
    ('SDA', B, SIG, [(5.70, 3.20), (13.10, 3.20), (13.97, 4.07), 'J1.6']),
    ('SCL', B, SIG, [(5.70, 4.15), (10.90, 4.15), (11.43, 4.68), 'J1.5']),
]

# Silkscreen labels for the header (on the back, readable from below, and
# on the front where there is room).
BACK_LABEL_Y = 3.75


def load_fp(fpid):
    lib, name = fpid.split(':')
    fp = pcbnew.FootprintLoad(os.path.join(FPDIR, lib + '.pretty'), name)
    assert fp, fpid
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def strip_silk(fp, fab_layer):
    """Move the reference to the fab layer and drop library silkscreen.

    The board is too dense for per-part silk; outlines live on the fab layer.
    """
    for f in fp.GetFields():
        if f.GetName() == 'Reference':
            f.SetLayer(fab_layer)
            f.SetTextSize(pcbnew.VECTOR2I(mm(0.5), mm(0.5)))
            f.SetTextThickness(mm(0.08))
            f.SetPosition(fp.GetPosition())
        elif f.GetName() == 'Value':
            f.SetVisible(False)
    # (Removing items via SWIG corrupts the type table, so move them instead.)
    for item in fp.GraphicalItems():
        if item.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            item.SetLayer(fab_layer)


def setup_rules(board):
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ds.m_MinClearance = mm(0.15)
    ds.m_TrackMinWidth = mm(0.15)
    ds.m_ViasMinSize = mm(0.5)
    ds.m_MinThroughDrill = mm(0.3)
    ds.m_ViasMinAnnularWidth = mm(0.1)
    ds.m_CopperEdgeClearance = mm(0.25)
    ds.m_HoleClearance = mm(0.2)
    ds.m_HoleToHoleMin = mm(0.25)
    ds.m_SilkClearance = mm(0)
    ds.m_MinSilkTextHeight = mm(0.5)
    ds.m_MinSilkTextThickness = mm(0.08)
    ds.m_SolderMaskExpansion = mm(0)
    ds.m_SolderMaskMinWidth = mm(0)
    ds.m_TentViasFront = True
    ds.m_TentViasBack = True
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(mm(0.15))       # 0.5 mm pitch LGA pads are 0.15 mm apart
    nc.SetTrackWidth(mm(SIG))
    nc.SetViaDiameter(mm(0.5))
    nc.SetViaDrill(mm(0.3))


def outline(board):
    r = CORNER_R
    segs = [((r, 0), (W - r, 0)), ((W, r), (W, H - r)),
            ((W - r, H), (r, H)), ((0, H - r), (0, r))]
    for a, b in segs:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        s.SetStart(P(*a))
        s.SetEnd(P(*b))
        board.Add(s)
    k = r * (1 - 0.7071068)
    arcs = [((0, r), (k, k), (r, 0)), ((W - r, 0), (W - k, k), (W, r)),
            ((W, H - r), (W - k, H - k), (W - r, H)), ((r, H), (k, H - k), (0, H - r))]
    for a, m, b in arcs:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        s.SetArcGeometry(P(*a), P(*m), P(*b))
        board.Add(s)


def text(board, s, x, y, layer, h=0.8, w=None, thick=0.12, just='center'):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(w or h), mm(h)))
    t.SetTextThickness(mm(thick))
    t.SetPosition(P(x, y))
    t.SetHorizJustify({'center': pcbnew.GR_TEXT_H_ALIGN_CENTER,
                       'left': pcbnew.GR_TEXT_H_ALIGN_LEFT,
                       'right': pcbnew.GR_TEXT_H_ALIGN_RIGHT}[just])
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)


def line(board, a, b, layer=pcbnew.F_SilkS, width=0.12):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetLayer(layer)
    s.SetWidth(mm(width))
    s.SetStart(P(*a))
    s.SetEnd(P(*b))
    board.Add(s)


def circle(board, c, r, layer=pcbnew.F_SilkS, width=0.12, fill=False):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_CIRCLE)
    s.SetLayer(layer)
    s.SetWidth(mm(width))
    s.SetCenter(P(*c))
    s.SetEnd(P(c[0] + r, c[1]))
    s.SetFilled(fill)
    board.Add(s)


def arrow(board, a, b, head=0.35, shaft=0.12):
    """Filled arrow from a to b as one polygon (avoids silk-overlap noise)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / n, dy / n
    px, py = -uy, ux
    hw, sw = head * 0.55, shaft / 2
    bx, by = b[0] - head * ux, b[1] - head * uy
    pts = [(a[0] + px * sw, a[1] + py * sw), (bx + px * sw, by + py * sw),
           (bx + px * hw, by + py * hw), b, (bx - px * hw, by - py * hw),
           (bx - px * sw, by - py * sw), (a[0] - px * sw, a[1] - py * sw)]
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_POLY)
    s.SetLayer(pcbnew.F_SilkS)
    s.SetWidth(0)
    s.SetFilled(True)
    s.SetPolyPoints([P(*q) for q in pts])
    board.Add(s)


def silk(board):
    """Silkscreen; coordinates are board coordinates."""
    # Header pin names: back side (visible when looking at the solder side).
    for i, name in enumerate(HEADER):
        x = 1.27 + 2.54 * i
        text(board, name.replace('+', ''), x, BACK_LABEL_Y + DY, pcbnew.B_SilkS, h=0.7, w=0.5)
    text(board, 'LSM6DSV32X', W / 2, 1.2, pcbnew.B_SilkS, h=0.8, w=0.6)
    text(board, 'I2C 0x6B', W / 2, 2.4, pcbnew.B_SilkS, h=0.7, w=0.5)
    text(board, 'JP1 cut: no I2C pull-ups', 6.3, 2.3 + DY, pcbnew.B_SilkS, h=0.55, w=0.45,
         thick=0.1)
    # Front, in the band between the mounting holes: name and axis marker.
    # U1 is rotated 180 deg, so +X points left and +Y points toward the
    # header (down in this view); Z comes out of the board.
    text(board, 'LSM6DSV32X', 8.2, 1.4, pcbnew.F_SilkS, h=0.8, w=0.6)
    o = (14.40, 1.00)
    arrow(board, (o[0] - 0.4, o[1]), (12.85, o[1]))
    arrow(board, (o[0], o[1] + 0.4), (o[0], 2.6))
    circle(board, o, 0.25, width=0.1)
    circle(board, o, 0.07, width=0.1)
    text(board, 'X', 12.45, o[1], pcbnew.F_SilkS, h=0.55, w=0.5, thick=0.1)
    text(board, 'Y', 14.90, 2.3, pcbnew.F_SilkS, h=0.55, w=0.5, thick=0.1)
    # U1 pin-1 dot (pin 1 is the bottom-right corner after rotation).
    circle(board, (13.25, 3.55 + DY), 0.1, fill=True)


def hole_keepout(board, center, r=2.0):
    """No copper under the M2 screw head / washer (both layers)."""
    import math
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu)
    ls.AddLayer(pcbnew.B_Cu)
    z.SetLayerSet(ls)
    z.SetDoNotAllowCopperPour(True)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ol = z.Outline()
    ol.NewOutline()
    for k in range(32):
        a = 2 * math.pi * k / 32
        ol.Append(mm(OX + center[0] + r * math.cos(a)), mm(OY + center[1] + r * math.sin(a)))
    board.Add(z)


def zone(board, net, layer):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in ((0, 0), (W, 0), (W, H), (0, H)):
        ol.Append(mm(OX + x), mm(OY + y))
    z.SetLocalClearance(mm(0.2))
    z.SetMinThickness(mm(0.2))
    z.SetThermalReliefGap(mm(0.2))
    z.SetThermalReliefSpokeWidth(mm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetAssignedPriority(0)
    board.Add(z)
    return z


def main():
    uuids = json.load(open(os.path.join(ROOT, 'tools', 'symbol_uuids.json')))
    path = os.path.join(ROOT, PROJECT + '.kicad_pcb')
    board = pcbnew.NewBoard(path)
    setup_rules(board)

    # Net names as eeschema derives them: power symbols give global names,
    # local labels on the root sheet become '/NAME', no-connect pins get
    # 'unconnected-(REF-PIN-PadN)'.
    def pcb_name(n):
        return n if n in POWER_NETS else '/' + n

    nets = {}
    for ref, (_, _, _, pins, _) in COMPONENTS.items():
        for pin, n in pins.items():
            if n is None:
                n = 'unconnected-(%s-%s-Pad%s)' % (ref, NC_PIN_NAMES[(ref, pin)], pin)
                pins[pin] = n
            if n not in nets:
                nets[n] = pcbnew.NETINFO_ITEM(board, n if n.startswith('unconn') else pcb_name(n))
                board.Add(nets[n])

    fps = {}
    for ref, (lib_id, value, fpid, pins, fields) in COMPONENTS.items():
        fp = load_fp(fpid)
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetPath(pcbnew.KIID_PATH('/' + uuids['symbols'][ref]))
        fp.SetSheetname('/')
        fp.SetSheetfile(PROJECT + '.kicad_sch')
        board.Add(fp)
        if ref == 'J1':
            # Bottom side; find the orientation that puts pad 1 left, pad 8 right.
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            for rot in (0, 90, 180, 270):
                fp.SetOrientationDegrees(rot)
                fp.SetPosition(P(0, 0))
                p1 = fp.FindPadByNumber('1').GetPosition()
                p8 = fp.FindPadByNumber('8').GetPosition()
                if p8.x - p1.x > mm(17) and abs(p8.y - p1.y) < mm(0.01):
                    break
            else:
                raise RuntimeError('J1 orientation')
            fp.SetPosition(fp.GetPosition() + (P(1.27, HY) - p1))
            strip_silk(fp, pcbnew.B_Fab)
        elif ref in HOLES:
            fp.SetPosition(P(*HOLES[ref]))
            strip_silk(fp, pcbnew.F_Fab)
        else:
            x, y, rot = PLACEMENT[ref]
            fp.SetPosition(C(x, y))
            fp.SetOrientationDegrees(rot)
            strip_silk(fp, pcbnew.F_Fab)
        fp.SetDNP(ref in DNP)
        for pad in fp.Pads():
            n = pins.get(pad.GetNumber())
            if n:
                pad.SetNet(nets[n])
        for k, v in fields.items():
            fp.SetField(k, v)
            f = fp.GetFieldByName(k)
            f.SetVisible(False)
            f.SetLayer(pcbnew.B_Fab if ref == 'J1' else pcbnew.F_Fab)
            f.SetPosition(fp.GetPosition())
        fps[ref] = fp

    def pt(p, net):
        if isinstance(p, str):
            ref, num = p.split('.')
            pad = fps[ref].FindPadByNumber(num)
            assert pad.GetNetCode() == nets[net].GetNetCode(), (p, pad.GetNetname(), net)
            return pad.GetPosition()
        return C(*p)

    layer_id = {F: pcbnew.F_Cu, B: pcbnew.B_Cu}
    for net, layer, width, pts in TRACKS:
        vs = [pt(p, net) for p in pts]
        for a, b in zip(vs, vs[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(a)
            t.SetEnd(b)
            t.SetWidth(mm(width))
            t.SetLayer(layer_id[layer])
            t.SetNet(nets[net])
            board.Add(t)

    for net, x, y in VIAS:
        v = pcbnew.PCB_VIA(board)
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetPosition(C(x, y))
        v.SetWidth(mm(0.5))
        v.SetDrill(mm(0.3))
        v.SetNet(nets[net])
        board.Add(v)

    outline(board)
    silk(board)
    for c in HOLES.values():
        hole_keepout(board, c)
    zones = [zone(board, nets['GND'], pcbnew.F_Cu), zone(board, nets['GND'], pcbnew.B_Cu)]
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())

    board.GetDesignSettings().SetAuxOrigin(P(0, H))   # fab origin: bottom-left
    board.GetDesignSettings().SetGridOrigin(P(0, H))
    tb = board.GetTitleBlock()
    tb.SetTitle('LSM6DSV32X Breakout')
    tb.SetRevision('1.0')
    tb.SetComment(0, '%.2f x %.2f mm, 2 layers, 1.6 mm FR4' % (W, H))
    pcbnew.SaveBoard(path, board)

    # Library silk was moved to the fab layer on purpose (no room on a board
    # this small), so don't warn that footprints differ from the library.
    pro_path = os.path.join(ROOT, PROJECT + '.kicad_pro')
    pro = json.load(open(pro_path))
    sev = pro['board']['design_settings']['rule_severities']
    sev['lib_footprint_mismatch'] = 'ignore'
    with open(pro_path, 'w') as f:
        json.dump(pro, f, indent=2)
    print('wrote', path)


if __name__ == '__main__':
    main()
