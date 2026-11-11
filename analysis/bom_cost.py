# per-board component cost at LCSC "10+" break (or 1+ when first break is 50+)
full = {
 "SMA x2 (BWSMA-KE-P001)":0.64, "RF ESD KLXES15AAA1":0.02, "SPDT BGS12P2L6 x2":0.76,
 "LNA_LB PSA4-5043+":1.91, "LNA_HB QPL9503":5.08, "0402 LPF/HPF + match passives":0.15,
 "Gain block GVA-63+":1.69, "1:2 balun H3-TCM2-63WX+":2.68, "RFFC5072TR13":15.62,
 "IF balun BD2425N50200AHF":0.87, "SAW SAFEA2G45MC0F0AR00":0.27, "TCXO TG2520SMN 40M":0.33,
 "ESP32-S31NRV16":5.01, "Flash GD25Q32ESIGR":0.72, "PHY YT8531DC-CA":1.24, "25 MHz xtal":0.10,
 "Magjack HR911130C":2.44, "USB-C + USBLC6 clone":0.24, "LDO AMS1117-3.3 (basic)":0.21,
 "LDO TPS7A2033 (RFFC)":0.21, "LDO TPS7A2045 (LNA/GB)":0.23, "misc passives/ferrites/LED":0.80,
}
lean = dict(full)
for k in ["LNA_HB QPL9503","Gain block GVA-63+","1:2 balun H3-TCM2-63WX+","LDO TPS7A2045 (LNA/GB)"]: lean.pop(k)
leanusb = dict(lean)
for k in ["PHY YT8531DC-CA","25 MHz xtal","Magjack HR911130C"]: leanusb.pop(k)
leanusb["misc passives/ferrites/LED"]=0.6
def fixed(nboards, uniq, xray_per_board, tht_joints=20, smt_joints=600, pcb=15.0):
    setup=25.56; stencil=8.21; load=1.53*uniq
    nx=xray_per_board*nboards
    rate=1.64 if nx<=10 else 0.82 if nx<=50 else 0.49 if nx<=200 else 0.33
    xray=nx*rate
    joints=nboards*(smt_joints*0.0016+tht_joints*0.0164)+ (3.58 if tht_joints else 0)
    tot=setup+stencil+load+xray+joints+pcb
    return tot/nboards, dict(pcb=pcb/nboards,setup_stencil=(setup+stencil)/nboards,loading=load/nboards,xray=xray/nboards,joints=joints/nboards)
for name,bom,uniq,xr,tht in [("FULL",full,50,9,20),("LEAN",lean,34,7,20),("LEAN-USB (no GbE)",leanusb,28,6,4)]:
    c=sum(bom.values())
    for n in (5,10):
        f,d=fixed(n,uniq,xr,tht)
        print(f"{name:18s} n={n:2d}: parts {c:6.2f} + fixed {f:6.2f} = {c+f:6.2f}  ({', '.join(f'{k} {v:.2f}' for k,v in d.items())})")
    print("   xray-per-type reading: fixed would be lower by", round((xr*5*0.82 - xr*1.64)/5,2), "per board at n=5")
