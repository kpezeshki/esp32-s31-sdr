#!/bin/bash
# multi-pass: rebuild placement, route, push failed nets to the front of the order; keep the best pass
cd /home/kaveh/claude_out_remote/esp32_sdr/hw
best=99999
for i in 1 2 3 4; do
  python3 build_pcb.py > /dev/null 2>&1
  python3 router.py > route_log_$i.txt 2>&1
  nf=$(grep -c "^FAIL" route_report.txt)
  echo "pass $i: failed $nf"
  if [ "$nf" -lt "$best" ]; then best=$nf; cp esp32_sdr_routed.kicad_pcb esp32_sdr_routed_best.kicad_pcb; cp route_report.txt route_report_best.txt; fi
  [ "$nf" -eq 0 ] && break
done
echo "best failed: $best"
