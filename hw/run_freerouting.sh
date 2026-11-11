#!/bin/bash
# Sandboxed Freerouting run (see claude_notes/FREEROUTING_AUDIT.md):
#   no network (PrivateNetwork), memory-capped systemd user unit, telemetry off twice, data dir in the project.
# usage: bash run_freerouting.sh <unit-name> <in.dsn> <out.ses> <log> [timeout_s]
set -e
unit=$1; dsn=$2; ses=$3; log=$4; tmo=${5:-4500}
HW=/home/kaveh/claude_out_remote/esp32_sdr/hw
FR=/home/kaveh/tools/freerouting
mkdir -p $HW/.freerouting
exec systemd-run --user --unit="$unit" --wait --collect -q \
  -p MemoryMax=3G -p MemorySwapMax=0 -p PrivateNetwork=yes -p PrivateUsers=yes -p RuntimeMaxSec="$tmo" \
  -p WorkingDirectory=$HW -p StandardOutput=file:$HW/$log -p StandardError=file:$HW/$log \
  $FR/jdk-21.0.13+9-jre/bin/java -Xmx2500m -Dhttps.proxyHost=127.0.0.1 -Dhttps.proxyPort=9 \
  -jar $FR/freerouting.jar --user_data_path=$HW/.freerouting \
  --gui.enabled=false --usage_and_diagnostic_data.disable_analytics=true --profile.allow_telemetry=false \
  --api_server.enabled=false -de "$dsn" -do "$ses" -mp 100
