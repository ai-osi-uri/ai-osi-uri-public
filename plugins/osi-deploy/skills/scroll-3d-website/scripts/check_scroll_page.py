"""Check a one-take scroll-film page (references/08-one-take-cinematic.md §6).

usage: python3 check_scroll_page.py path/to/index.html  [chrome_path]
Assumes: <video id="movie">, sections with [data-t0][data-t1] and an id, pinned text panes (.pane.on .k-blk).
Prints, for PC and phone: idle film time, per-section (text y before/after a scroll, film time before/after,
whether the active pane fits the screen), inner scroll containers, horizontal overflow, page errors.
Screenshots go to /tmp/check_<device>_<section>.png.
"""
import asyncio, sys
from playwright.async_api import async_playwright

PAGE = sys.argv[1]
CHROME = sys.argv[2] if len(sys.argv) > 2 else "/usr/bin/google-chrome"
DEVICES = {"pc": (1440, 900), "sp": (390, 844)}

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        bad = 0
        for name, (w, h) in DEVICES.items():
            pg = await b.new_page(viewport={"width": w, "height": h})
            errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
            url = PAGE if PAGE.startswith("http") else "file://" + PAGE
            await pg.goto(url)
            await pg.wait_for_timeout(3500)
            t_a = await pg.evaluate("document.getElementById('movie').currentTime")
            await pg.wait_for_timeout(1500)
            t_b = await pg.evaluate("document.getElementById('movie').currentTime")
            if abs(t_b - t_a) > 0.01: bad += 1; print(name, "NG: film moves while idle")
            ids = await pg.evaluate("[...document.querySelectorAll('main [data-t0]')].map(s=>s.id)")
            for sec in ids[1:]:
                await pg.evaluate(f"(()=>{{const s=document.getElementById('{sec}'); scrollTo(0, s.offsetTop + s.offsetHeight*0.35 - innerHeight*0.5)}})()")
                await pg.wait_for_timeout(1700)
                y1 = await pg.evaluate("(()=>{const e=document.querySelector('.pane.on .k-blk'); return e? Math.round(e.getBoundingClientRect().top):null})()")
                t1 = await pg.evaluate("document.getElementById('movie').currentTime")
                await pg.screenshot(path=f"/tmp/check_{name}_{sec}.png")
                await pg.evaluate("scrollBy(0, innerHeight*0.2)"); await pg.wait_for_timeout(900)
                y2 = await pg.evaluate("(()=>{const e=document.querySelector('.pane.on .k-blk'); return e? Math.round(e.getBoundingClientRect().top):null})()")
                t2 = await pg.evaluate("document.getElementById('movie').currentTime")
                fit = await pg.evaluate("(()=>{const p=document.querySelector('.pane.on'); if(!p) return null; const r=[...p.querySelectorAll('.k-blk')].map(e=>e.getBoundingClientRect()); return {top:Math.round(Math.min(...r.map(x=>x.top))), bottom:Math.round(Math.max(...r.map(x=>x.bottom))), h:innerHeight}})()")
                ok = (y1 == y2) and (t2 > t1) and fit and fit["top"] >= 0 and fit["bottom"] <= fit["h"]
                bad += 0 if ok else 1
                print(name, sec, "OK" if ok else "NG", "| text y", y1, "->", y2, "| film", round(t1, 2), "->", round(t2, 2), "| fits", fit)
            inner = await pg.evaluate("""[...document.querySelectorAll('*')].filter(e=>{const s=getComputedStyle(e);return /(auto|scroll)/.test(s.overflowY+s.overflowX) && e.scrollHeight>e.clientHeight+1 && e!==document.documentElement && e!==document.body}).length""")
            hs = await pg.evaluate("document.documentElement.scrollWidth>innerWidth")
            bad += (inner > 0) + bool(hs) + (len(errs) > 0)
            print(name, "inner scrollers:", inner, "| horizontal overflow:", hs, "| errors:", errs)
        await b.close()
        print("RESULT:", "PASS" if bad == 0 else f"FAIL ({bad})")
        sys.exit(1 if bad else 0)

asyncio.run(main())
