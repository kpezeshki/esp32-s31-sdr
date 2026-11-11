import sys, json, subprocess
def q(kw, n=8):
    body=json.dumps({"keyword":kw,"currentPage":1,"pageSize":n})
    out=subprocess.run(["curl","-s","-m","40","-A","Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
      "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList",
      "-H","content-type: application/json","-d",body],capture_output=True,text=True).stdout
    try: d=json.loads(out)
    except Exception: print(kw,"ERR",out[:200]); return
    lst=((d.get("data") or {}).get("componentPageInfo") or {}).get("list") or []
    print(f"== {kw}: {len(lst)} hits")
    for c in lst:
        pr=c.get("componentPrices") or []
        ps=" ".join(f"{p['startNumber']}+:{p['productPrice']}" for p in pr[:5])
        lib=c.get("componentLibraryType"); pref="pref" if c.get("preferredComponentFlag") else ""
        print(f"  {c.get('componentCode')} | {c.get('componentBrandEn')} | {c.get('componentModelEn')} | {c.get('componentSpecificationEn')} | stock {c.get('stockCount')} | {lib}{pref} | {ps} | {c.get('noBuyReason') or ''} | {(c.get('describe') or '')[:60]}")
for kw in sys.argv[1:]: q(kw)
