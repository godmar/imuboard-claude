#!/usr/bin/env python3
"""Convert KiCad's position and BOM CSVs to JLCPCB's assembly formats.

Layouts follow JLCPCB's sample files (JLCSMT_Sample_CPL1.xlsx,
Sample-BOM_JLCSMT.xlsx):
  CPL: Designator | Mid X | Mid Y | Layer | Rotation   ("14.2000mm", "Top", 180)
  BOM: Comment | Designator | Footprint | JLCPCB Part #（optional）
Both are written as .xlsx (like the samples) and .csv.

Only parts in KiCad's top-side position file are included; the THT header
J1 is fitted by hand.  LCSC part numbers come from an 'LCSC' field in
design.py (empty = choose the part in JLCPCB's web UI).

usage: jlc_files.py kicad_pos.csv kicad_bom.csv out_prefix
"""
import csv
import sys

import xlsx
from design import COMPONENTS

BOM_PART_HDR = 'JLCPCB Part #（optional）'   # full-width parens, as in the sample


def expand(refs):
    """'C1,R1-R3' -> ['C1', 'R1', 'R2', 'R3'] (KiCad compresses runs)."""
    out = []
    for part in refs.split(','):
        if '-' in part:
            a, b = part.split('-')
            pre = a.rstrip('0123456789')
            out += ['%s%d' % (pre, i) for i in range(int(a[len(pre):]), int(b[len(pre):]) + 1)]
        else:
            out.append(part)
    return out


def cpl_rows(src):
    rows = [['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation']]
    with open(src, newline='') as f:
        for r in csv.DictReader(f):
            rot = float(r['Rot']) % 360
            rows.append([r['Ref'], '%.4fmm' % float(r['PosX']), '%.4fmm' % float(r['PosY']),
                         r['Side'].capitalize(), int(rot) if rot.is_integer() else rot])
    return rows


def bom_rows(src, placed):
    rows = [['Comment', 'Designator', 'Footprint', BOM_PART_HDR]]
    with open(src, newline='') as f:
        for r in csv.DictReader(f):
            refs = [x for x in expand(r['Refs']) if x in placed]
            if not refs:
                continue
            fields = COMPONENTS[refs[0]][4]
            rows.append([fields.get('MPN', r['Value']), ','.join(refs),
                         r['Footprint'].split(':')[-1], fields.get('LCSC', '')])
    return rows


def save(rows, prefix):
    xlsx.write(prefix + '.xlsx', rows)
    with open(prefix + '.csv', 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows(rows)


def main(pos, bom, prefix):
    cpl = cpl_rows(pos)
    save(cpl, prefix + '_cpl_jlcpcb')
    save(bom_rows(bom, {r[0] for r in cpl[1:]}), prefix + '_bom_jlcpcb')


if __name__ == '__main__':
    main(*sys.argv[1:4])
