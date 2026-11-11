#!/bin/bash
# Gerbers + drill + zip for JLC, per board.  bash fab_export.sh a|b
set -e
l=$1; cd /home/kaveh/claude_out_remote/esp32_sdr/hw/board_$l
pcb=esp32sdr_${l}_routed.kicad_pcb
rm -rf fab/gerber; mkdir -p fab/gerber
kicad-cli pcb export gerbers --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts \
   --subtract-soldermask --no-x2 --use-drill-file-origin -o fab/gerber/ $pcb >/dev/null
kicad-cli pcb export drill --format excellon --excellon-separate-th --generate-map --map-format gerberx2 -o fab/gerber/ $pcb >/dev/null
(cd fab/gerber && rm -f ../esp32sdr_${l}_gerbers.zip && zip -q ../esp32sdr_${l}_gerbers.zip *)
ls fab/gerber | wc -l; ls -la fab/esp32sdr_${l}_gerbers.zip
