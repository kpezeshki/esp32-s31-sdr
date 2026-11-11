# 2026-11-10: two-board layout and routing

- Both boards are routed and DRC-clean under JLC basic 4L rules (D22). Fab outputs are in hw/board_{a,b}/fab, images in hw/board_{a,b}/shots.
- Freerouting would not converge on A on its own (it left 7–20 unrouted). Two things fixed it:
  - deterministic module inner-pad escapes and scripted RGMII lanes (TX on B.Cu, RX on In2);
  - D21, dropping the TX 33R.

  On B, three scripted fixes plus pinning the PLL loop filter next to the RFFC5072 did the job.
- Freerouting was audited (claude_notes/FREEROUTING_AUDIT.md): not malicious, but it does an update check. Run it only via hw/run_freerouting.sh (PrivateNetwork, 3 GB cap).
- KiCad 10 SWIG gotcha: after any b.Remove(), GetTracks()/Zones() break. Collect your lists first.
- Twice this session, Claude Code's memory reaper killed background shells. The cause was other projects' jobs (~34 GB), not ours. A systemd unit survives the reap.
- Open before ordering:
  - A: USB HS pair skew and coupling
  - A: MDI pair tidy
  - B: REFCLK DNP stub
  - B: JLC CPL rotation and DFM check
  - U1 sourcing
