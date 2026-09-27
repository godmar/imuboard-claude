#!/bin/sh
# Regenerate everything and write fabrication outputs to fab/.
set -e
cd "$(dirname "$0")/.."
P=lsm6dsv32x_breakout

python3 tools/gen_schematic.py
python3 tools/gen_pcb.py 2>&1 | grep -v 'memory leak' || true

kicad-cli sch erc --severity-all --exit-code-violations -o fab/erc.rpt $P.kicad_sch
kicad-cli pcb drc --severity-all --schematic-parity --exit-code-violations -o fab/drc.rpt $P.kicad_pcb

rm -rf fab/gerbers && mkdir -p fab/gerbers
kicad-cli pcb export gerbers --layers F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
    --subtract-soldermask --use-drill-file-origin -o fab/gerbers/ $P.kicad_pcb
kicad-cli pcb export drill --format excellon --drill-origin plot --excellon-separate-th \
    --generate-map --map-format gerberx2 -o fab/gerbers/ $P.kicad_pcb
(cd fab/gerbers && rm -f ../${P}_gerbers.zip && zip -q ../${P}_gerbers.zip *)

kicad-cli pcb export pos --side front --format csv --units mm --use-drill-file-origin \
    --exclude-dnp -o fab/${P}_pos_top.csv $P.kicad_pcb
kicad-cli sch export bom --fields 'Reference,Value,Footprint,MPN,Note,${QUANTITY}' \
    --labels 'Refs,Value,Footprint,MPN,Note,Qty' --group-by Value,Footprint \
    --exclude-dnp -o fab/${P}_bom.csv $P.kicad_sch

kicad-cli sch export pdf -o fab/${P}_schematic.pdf $P.kicad_sch
kicad-cli pcb export pdf --layers F.Cu,F.Silkscreen,F.Fab,Edge.Cuts --mode-single \
    -o fab/${P}_assembly_top.pdf $P.kicad_pcb
kicad-cli pcb render --side top --width 1600 --height 700 --zoom 1.8 -o fab/render_top.png $P.kicad_pcb
kicad-cli pcb render --side bottom --width 1600 --height 700 --zoom 1.8 -o fab/render_bottom.png $P.kicad_pcb
echo "fab outputs in fab/"
