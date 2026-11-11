#!/usr/bin/env python3
"""Route the digital/power nets with Freerouting (needs your OK to run it: it is an external Java tool).
 1. lock all scripted RF tracks/vias in esp32_sdr.kicad_pcb, export Specctra DSN (fab/esp32_sdr.dsn)
 2. run:  ~/tools/freerouting/jdk-21.0.13+9-jre/bin/java -jar ~/tools/freerouting/freerouting.jar -de fab/esp32_sdr.dsn -do fab/esp32_sdr.ses -mp 30
 3. import the SES, save esp32_sdr_fr.kicad_pcb, fill zones, DRC.
Usage: python3 fr_route.py export | import"""
import os, sys, subprocess, pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
FAB = os.path.join(HERE, "fab"); os.makedirs(FAB, exist_ok=True)
if sys.argv[1] == "export":
    subprocess.run([sys.executable, os.path.join(HERE, "build_pcb.py")], env=dict(os.environ, NO_OUTER_POUR="1"), capture_output=True)
    b = pcbnew.LoadBoard(os.path.join(HERE, "esp32_sdr_nopour.kicad_pcb"))   # outer GND pours re-added after routing
    for t in b.GetTracks(): t.SetLocked(True)          # RF microstrip + ladder vias stay exactly as EM-simulated
    for fp in b.GetFootprints(): fp.SetLocked(True)
    pcbnew.SaveBoard(os.path.join(HERE, "esp32_sdr_locked.kicad_pcb"), b)
    ok = pcbnew.ExportSpecctraDSN(b, os.path.join(FAB, "esp32_sdr.dsn"))
    print("DSN export:", ok, os.path.join(FAB, "esp32_sdr.dsn"))
elif sys.argv[1] == "import":
    b = pcbnew.LoadBoard(os.path.join(HERE, "esp32_sdr_locked.kicad_pcb"))
    ok = pcbnew.ImportSpecctraSES(b, os.path.join(FAB, "esp32_sdr.ses"))
    src = pcbnew.LoadBoard(os.path.join(HERE, "esp32_sdr.kicad_pcb"))
    for z in src.Zones():
        if z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu) and not z.GetIsRuleArea():
            nz = z.Duplicate(); nz.SetNet(b.FindNet("GND")); b.Add(nz)
    out = os.path.join(HERE, "esp32_sdr_fr.kicad_pcb"); pcbnew.SaveBoard(out, b)
    print("SES import:", ok, out)
    subprocess.run(["kicad-cli", "pcb", "drc", "--refill-zones", "--save-board", "-o", os.path.join(FAB, "drc_fr.rpt"), out])
