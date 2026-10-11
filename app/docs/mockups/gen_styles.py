"""Builds the 'styles' brainstorm screen: 3 styles x 3 screens, maps drawn from the real fixture streets."""
import json
import math
import sys

FIX = sys.argv[1]
OUT = sys.argv[2]

segs = json.load(open(f"{FIX}/segments.geojson"))["features"]
band = {r["segment_id"]: r["band"] for r in json.load(open(f"{FIX}/risk.json"))}
route = json.load(open(f"{FIX}/routes.json"))[0]["geometry"]["coordinates"]

LON0, LON1, LAT0, LAT1 = 80.2161626, 80.2226964, 12.9711221, 12.9789186
KX = math.cos(math.radians(12.975))
HAZARD = (80.2212061, 12.9777428)
HOME = (80.2161626, 12.9711221)
OFFICE = (80.2164319, 12.9747602)
BIKE = (80.22105, 12.97758)


def projector(w, h, pad=34):
    span_x, span_y = (LON1 - LON0) * KX, LAT1 - LAT0
    s = min((w - 2 * pad) / span_x, (h - 2 * pad) / span_y)
    ox = (w - span_x * s) / 2
    oy = (h - span_y * s) / 2
    return lambda lon, lat: (ox + (lon - LON0) * KX * s, oy + (LAT1 - lat) * s), s


def path(pts):
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)


def map_svg(w, h, c, show_route=False, pins=True):
    """c: dict of colours: bg, street, low, watch, likely, flooded, route, hazard, pin, label."""
    p, s = projector(w, h)
    out = [f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" style="display:block">',
           f'<rect width="{w}" height="{h}" fill="{c["bg"]}"/>']
    # faint block texture so the map doesn't float in a void
    import random
    rnd = random.Random(7)
    out.append(f'<g stroke="{c["base"]}" stroke-linecap="round" fill="none" transform="rotate(-9 {w/2} {h/2})">')
    for i, x in enumerate(range(-60, w + 60, 30)):
        y0 = rnd.randint(-80, 40); y1 = h + rnd.randint(-40, 80)
        out.append(f'<path d="M{x + rnd.randint(-6, 6)} {y0} L{x + rnd.randint(-10, 10)} {y1}" stroke-width="{6 if i % 4 == 1 else 3}"/>')
    for j, y in enumerate(range(-60, h + 60, 26)):
        x0 = rnd.randint(-80, 60); x1 = w + rnd.randint(-60, 80)
        out.append(f'<path d="M{x0} {y + rnd.randint(-5, 5)} L{x1} {y + rnd.randint(-8, 8)}" stroke-width="{6 if j % 5 == 2 else 2.5}"/>')
    out.append('</g>')
    g = [(path([p(*pt) for pt in f["geometry"]["coordinates"]]), band.get(f["id"], "low")) for f in segs]
    out.append('<g fill="none" stroke-linecap="round" stroke-linejoin="round">')
    for d, _ in g:
        out.append(f'<path d="{d}" stroke="{c["street"]}" stroke-width="9"/>')
    for d, b in g:
        if b == "flooded":
            out.append(f'<path d="{d}" stroke="{c["flooded"]}" stroke-width="16" stroke-opacity=".25"/>')
            out.append(f'<path d="{d}" stroke="{c["flooded"]}" stroke-width="8"/>')
        else:
            out.append(f'<path d="{d}" stroke="{c[b]}" stroke-width="{4.5 if b == "likely" else 3.5}"/>')
    if show_route:
        rd = path([p(*pt) for pt in route])
        out.append(f'<path d="{rd}" stroke="{c["route"]}" stroke-width="14" stroke-opacity=".22"/>')
        out.append(f'<path d="{rd}" stroke="{c["route"]}" stroke-width="5.5"/>')
        out.append(f'<path d="{rd}" stroke="#fff" stroke-width="1.6" stroke-dasharray="2 7" stroke-opacity=".9"/>')
    out.append("</g>")
    hx, hy = p(*HAZARD)
    out.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{max(30 / 111000 * s, 9):.1f}" fill="{c["hazard"]}" fill-opacity=".14" stroke="{c["hazard"]}" stroke-dasharray="3 3"/>')
    out.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="4.5" fill="{c["hazard"]}" stroke="#fff" stroke-width="1.5"/>')
    if show_route:
        for pt, lab in ((route[0], "A"), (route[-1], "B")):
            x, y = p(*pt)
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="{c["route"]}" stroke="#fff" stroke-width="2"/>'
                       f'<text x="{x:.1f}" y="{y + 3.3:.1f}" text-anchor="middle" font-size="9" font-weight="700" fill="#fff" font-family="sans-serif">{lab}</text>')
    elif pins:
        for pt, lab in ((HOME, "Home"), (BIKE, "Bike"), (OFFICE, "Office")):
            x, y = p(*pt)
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{c["pin"]}" stroke="#fff" stroke-width="2"/>'
                       f'<text x="{x + 9:.1f}" y="{y + 3.5:.1f}" font-size="9.5" font-weight="700" fill="{c["label"]}" font-family="sans-serif">{lab}</text>')
    out.append("</svg>")
    return "".join(out)


I = {  # 24px line icons, stroke=currentColor
    "bell": "M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.94 1.94 0 0 0 3.4 0",
    "camera": "M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3zM15 13a3 3 0 1 1-6 0 3 3 0 0 1 6 0",
    "route": "M6 21a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM18 7a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM6 17V11a4 4 0 0 1 4-4h6M18 7v6a4 4 0 0 1-4 4h-6",
    "map": "M9 4 3 6v14l6-2 6 2 6-2V4l-6 2zM9 4v14M15 6v14",
    "home": "M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z",
    "arrow": "M7 17 17 7M8 7h9v9",
    "back": "M15 18l-6-6 6-6",
    "check": "M5 12.5l4.5 4.5L19 7.5",
    "x": "M6 6l12 12M18 6 6 18",
    "drop": "M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z",
    "bike": "M5.5 20a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18.5 20a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM5.5 17l3.5-7h5l4.5 7M9 10 7.5 7H6M14 10l-1.5-3H15",
    "car": "M4 16v-4l2-5h12l2 5v4zM3 16h18M6.5 16v2.5M17.5 16v2.5M7.5 12.5h.01M16.5 12.5h.01",
    "amb": "M2 17V7h12v10M14 10h4l4 4v3h-8M5 12h6M8 9v6M6 19.5a1.5 1.5 0 1 0 0-3M17 19.5a1.5 1.5 0 1 0 0-3",
    "warn": "M12 4 2.5 20h19zM12 10v4.5M12 17.5h.01",
    "school": "M3 9l9-5 9 5-9 5zM7 11v5c0 1 2.5 3 5 3s5-2 5-3v-5",
    "office": "M4 21V5a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v16M15 9h4a1 1 0 0 1 1 1v11M8 8h3M8 12h3M8 16h3M3 21h18",
    "rain": "M8 19l-1 2M12 19l-1 2M16 19l-1 2M7 16a5 5 0 1 1 1-9.9A6 6 0 0 1 19 9a3.5 3.5 0 0 1-1 7z",
    "spark": "M12 3v4M12 17v4M3 12h4M17 12h4",
}


def ic(name, size=18, sw=1.8):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"><path d="{I[name]}"/></svg>')


def body(water_top, skin, water, line, w=92, h=200, wave=True):
    """A standing figure with water to `water_top` (y in 0..220 space). Knee is ~158."""
    wv = (f'<path d="M0 {water_top} q12 -6 25 0 t25 0 t25 0 t25 0 V220 H0z" fill="{water}"/>' if wave
          else f'<rect y="{water_top}" width="100" height="{220 - water_top}" fill="{water}"/>')
    return f'''<svg viewBox="0 0 100 220" width="{w}" height="{h}">
      <g fill="{skin}"><circle cx="50" cy="20" r="14"/><rect x="34" y="38" width="32" height="74" rx="13"/>
      <rect x="21" y="42" width="11" height="64" rx="5.5"/><rect x="68" y="42" width="11" height="64" rx="5.5"/>
      <rect x="36" y="104" width="13" height="110" rx="6.5"/><rect x="51" y="104" width="13" height="110" rx="6.5"/></g>
      {wv}
      <g stroke="{line}" stroke-width="1" stroke-dasharray="2 3"><path d="M0 200H100"/><path d="M0 110H100"/></g>
    </svg>'''


def waves(colors, heights, w=268, h=200, amp=10, shift=0):
    """Layered illustrated waves, back to front."""
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}" preserveAspectRatio="none" style="display:block">']
    for i, (col, top) in enumerate(zip(colors, heights)):
        ph = (i * 37 + shift) % 60
        d = f"M0 {top} " + " ".join(
            f"Q{x + 22 - ph % 22:.0f} {top - amp + (i % 2) * 4} {x + 44:.0f} {top} T{x + 88:.0f} {top}" for x in range(-44, w + 88, 88)
        ) + f" V{h} H0z"
        out.append(f'<path d="{d}" fill="{col}"/>')
    out.append("</svg>")
    return "".join(out)


TA = {"places": "உங்கள் இடங்கள்", "knee": "முழங்கால் அளவு நீர்",
      "move": "உங்கள் பைக்கை விஜயநகர் 1வது மெயின் ரோட்டுக்கு நகர்த்துங்கள்",
      "reason": "முழங்கால் அளவு நீர் உள்ள வேளச்சேரி மெயின் ரோடு தவிர்க்கப்பட்டது",
      "velachery": "வேளச்சேரி"}

# ---------------------------------------------------------------- style 1: Glacier glass
M1 = dict(bg="#E4EFF7", base="#F4F9FC", grid="#DCE9F3", street="#FFFFFF", low="#8FA9BF", watch="#F2A93B", likely="#EF5B3B",
          flooded="#0B5BB5", route="#1592E6", hazard="#E5322D", pin="#0D2033", label="#0D2033")
M2 = dict(bg="#0C2347", base="#132D57", grid="#0F2850", street="#183764", low="#3D6C8F", watch="#F2B34A", likely="#FF6A45",
          flooded="#59D8E6", route="#4FD1D9", hazard="#FF4D4D", pin="#FFFFFF", label="#DDEBF5")
M3 = dict(bg="#EEF4F8", base="#FFFFFF", grid="#E6EEF4", street="#FFFFFF", low="#A9BCCB", watch="#F2A93B", likely="#EB5A3C",
          flooded="#1557A8", route="#0E7BD8", hazard="#E5322D", pin="#0B1E31", label="#0B1E31")

CSS = r"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Sofia+Sans:wght@400;500;600;700;800&family=Outfit:wght@300;400;500;600;700&family=Urbanist:wght@400;500;600;700;800&family=Noto+Sans+Tamil:wght@400;500;600&display=swap" rel="stylesheet">
<style>
.st{background:var(--bg-secondary);border-radius:22px;padding:22px 22px 26px;margin:22px 0 34px;cursor:pointer;border:2px solid transparent}
.st.selected{border-color:#1592E6}
.st h3{margin:0 0 4px;font-size:20px}.st .why{margin:0 0 18px;opacity:.75;font-size:14px;line-height:1.5;max-width:820px}
.row3{display:flex;gap:26px;justify-content:center;flex-wrap:wrap}
.cap{text-align:center;font-size:12.5px;opacity:.7;margin-top:12px}
.ph{width:268px;height:580px;border-radius:38px;overflow:hidden;position:relative;box-shadow:0 0 0 8px #0d0d0f,0 22px 44px rgba(0,0,0,.35)}
.ph .sb{display:flex;justify-content:space-between;padding:12px 24px 0;font-size:11px;font-weight:700;position:relative;z-index:3}
.ta{font-family:'Noto Sans Tamil',sans-serif}
.abs{position:absolute}
/* ---------- S1 glacier ---------- */
.s1{font-family:'Sofia Sans',sans-serif;color:#0D2033;background:linear-gradient(180deg,#CBE2F2 0%,#E7F2FA 55%,#D7E9F5 100%)}
.s1 .gl{background:rgba(255,255,255,.58);border:1px solid rgba(255,255,255,.9);box-shadow:0 8px 20px rgba(30,80,130,.13),inset 0 1px 0 #fff;backdrop-filter:blur(14px)}
.s1 .c{width:40px;height:40px;border-radius:50%;display:grid;place-items:center}
.s1 .blue{background:linear-gradient(160deg,#2AA6F2,#0E7FD0);color:#fff;box-shadow:0 8px 18px rgba(21,146,230,.35)}
.s1 .red{background:linear-gradient(160deg,#FF6A55,#E0322A);color:#fff;box-shadow:0 8px 18px rgba(224,50,42,.35)}
.s1 .muted{color:#5E7487}
.s1 .pill{white-space:nowrap;border-radius:22px;padding:8px 14px;font-size:12.5px;font-weight:600}
/* ---------- S2 deep tide ---------- */
.s2{font-family:'Outfit',sans-serif;color:#fff;background:linear-gradient(180deg,#5F8FAE 0%,#3B6E93 30%,#1C4A75 60%,#0A1F44 100%)}
.s2 .t{color:#4FD1D9}.s2 .muted{color:#A9C6DB}
.s2 .cb{width:48px;height:48px;border-radius:50%;display:grid;place-items:center;background:#2FA9B8;color:#fff;box-shadow:0 0 0 6px rgba(79,209,217,.16)}
/* ---------- S3 tide glass ---------- */
.s3{font-family:'Urbanist',sans-serif;color:#0B1E31;background:linear-gradient(180deg,#F4F8FB 0%,#E3EEF5 60%,#CFE2EF 100%)}
.s3 .gl{background:rgba(255,255,255,.68);border:1px solid rgba(255,255,255,.95);box-shadow:0 10px 26px rgba(20,70,120,.12),inset 0 1px 0 #fff;backdrop-filter:blur(16px)}
.s3 .muted{color:#5B7084}
.s3 .chip{white-space:nowrap;border-radius:999px;padding:5px 10px;font-size:11px;font-weight:700}
</style>
"""


def sb(color="inherit"):
    return f'<div class="sb" style="color:{color}"><span>02:00</span><span>5G ▮▮▮ ▭</span></div>'


def veh_row(cls_ok, cls_no, size=44, label_color="inherit"):
    items = [("bike", "Bike", False), ("car", "Car", False), ("amb", "Ambulance", True)]
    out = []
    for icn, lab, ok in items:
        out.append(f'''<div style="text-align:center;flex:1"><div style="position:relative;width:{size}px;height:{size}px;margin:0 auto;border-radius:50%;display:grid;place-items:center" class="{cls_ok if ok else cls_no}">{ic(icn, 20)}
          <span style="position:absolute;right:-3px;bottom:-3px;width:18px;height:18px;border-radius:50%;display:grid;place-items:center;background:{"#18A957" if ok else "#E5322D"};color:#fff;border:2px solid #fff">{ic("check" if ok else "x", 11, 3)}</span></div>
          <div style="font-size:11px;margin-top:6px;font-weight:600;color:{label_color}">{lab}</div></div>''')
    return '<div style="display:flex;gap:6px">' + "".join(out) + "</div>"


# ================= S1 GLACIER GLASS =================
s1_home = f'''<div class="ph s1">{sb()}
  <div class="abs" style="left:-10px;top:-18px;opacity:.55;color:#7FC0EE">{ic("drop", 90, .8)}</div>
  <div style="display:flex;justify-content:space-between;align-items:center;padding:14px 16px 0;position:relative">
    <div style="display:flex;gap:8px"><div class="c gl">{ic("bell", 17)}</div><div class="c gl ta" style="font-weight:600">த</div></div>
    <div style="text-align:right"><div style="font-weight:700;font-size:15px">Velachery</div><div class="muted" style="font-size:11.5px">Replay · 4 Dec, 02:00</div></div>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:center;padding:16px 16px 10px">
    <div><div style="font-size:21px;font-weight:700">Your places</div><div class="ta muted" style="font-size:11px">{TA["places"]}</div></div>
    <div style="display:flex;gap:8px"><div class="c gl">{ic("map", 17)}</div><div class="c red" style="font-weight:800;font-size:11px">SOS</div></div>
  </div>
  <div class="gl" style="margin:0 12px;border-radius:22px;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;background:linear-gradient(120deg,rgba(255,255,255,.7),rgba(170,214,245,.6))">
    <div><div style="font-weight:700;font-size:14px">Cyclone Michaung</div><div class="muted" style="font-size:11px">1 storm hour every 10 s</div>
      <div style="display:flex;gap:10px;margin-top:10px">
        {''.join(f'<div style="text-align:center"><div style="width:36px;height:36px;border-radius:50%;border:2.5px solid {col};display:grid;place-items:center;font-size:11px;font-weight:800;background:rgba(255,255,255,.7)">{v}</div><div class="muted" style="font-size:9.5px;margin-top:3px">{l}</div></div>' for v, l, col in (("18", "mm/h", "#1592E6"), ("140", "72 h mm", "#F2A93B"), ("Hi", "Tide", "#18A0B0")))}
      </div></div>
    <div style="width:84px;height:84px;border-radius:50%;background:conic-gradient(#1592E6 0 47%,rgba(255,255,255,.6) 47% 100%);display:grid;place-items:center">
      <div class="gl" style="width:66px;height:66px;border-radius:50%;display:grid;place-items:center;text-align:center"><div><div style="font-size:17px;font-weight:800">02:00</div><div class="muted" style="font-size:9px">hour 14 / 30</div></div></div></div>
  </div>
  <div style="height:12px"></div>
  <div style="margin:0 12px;height:162px;border-radius:26px;position:relative;overflow:hidden;color:#fff;background:linear-gradient(165deg,#3C9FE0 0%,#0B5BB5 70%)">
    <div class="abs" style="left:0;right:0;bottom:0">{waves(["rgba(255,255,255,.18)", "rgba(255,255,255,.14)", "rgba(6,40,95,.35)"], [30, 44, 60], h=86, amp=8)}</div>
    {''.join(f'<span class="abs" style="left:{x}px;top:{y}px;width:{r}px;height:{r}px;border-radius:50%;border:1px solid rgba(255,255,255,.55)"></span>' for x, y, r in ((170, 40, 9), (196, 66, 6), (150, 96, 5), (214, 104, 8), (184, 120, 4)))}
    <div class="abs gl" style="right:12px;top:12px;width:38px;height:38px;border-radius:50%;display:grid;place-items:center;color:#0B5BB5">{ic("arrow", 17)}</div>
    <div style="padding:14px 16px;position:relative">
      <div style="font-size:11.5px;opacity:.9">(Flooded · knee-deep)</div>
      <div style="font-size:25px;font-weight:700;line-height:1.05;margin-top:4px">Bike<br>parking</div>
      <div style="margin-top:12px;display:inline-block;padding:7px 12px;border-radius:18px;background:rgba(255,255,255,.22);border:1px solid rgba(255,255,255,.5);font-size:11.5px;font-weight:600">Move it to Vijayanagar 1st Main Rd</div>
    </div>
  </div>
  <div class="gl" style="margin:10px 12px 0;border-radius:20px;padding:11px 14px;display:flex;justify-content:space-between;align-items:center">
    <div style="display:flex;gap:10px;align-items:center"><div class="c" style="background:#FDE3DC;color:#E0452A">{ic("home", 17)}</div><div><div style="font-weight:700;font-size:13.5px">Home</div><div class="muted" style="font-size:11px">32 mm due · floods at 68 mm</div></div></div>
    <div style="text-align:right;color:#E0452A;font-weight:800;font-size:13px">1h 40m<div style="font-size:9.5px;font-weight:600">LIKELY</div></div></div>
  <div class="abs" style="left:0;right:0;bottom:14px;display:flex;justify-content:center;gap:10px">
    <div class="c blue" style="width:48px;height:48px">{ic("home", 19)}</div><div class="c gl" style="width:48px;height:48px">{ic("map", 19)}</div>
    <div class="c gl" style="width:48px;height:48px">{ic("camera", 19)}</div><div class="c gl" style="width:48px;height:48px">{ic("route", 19)}</div></div>
</div>'''

s1_depth = f'''<div class="ph s1">{sb()}
  <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px 0">
    <div class="c gl">{ic("back", 17)}</div><div style="font-weight:700">Your report</div><div class="c gl ta" style="font-weight:600">த</div></div>
  <div style="margin:10px 12px 0;height:96px;border-radius:22px;overflow:hidden;position:relative;background:linear-gradient(180deg,#8A8F86 0%,#6E6A55 45%,#57503B 100%)">
    <div class="abs" style="left:30px;top:18px;width:70px;height:70px;border-radius:50%;border:12px solid #1E1E1C;opacity:.85"></div><div class="abs" style="right:12px;top:10px;font-size:10px;color:rgba(255,255,255,.75);font-weight:600">your photo · 01:48</div>
    <div class="abs" style="left:0;right:0;top:56px;bottom:0;background:linear-gradient(180deg,rgba(120,105,70,.92),rgba(80,70,45,.96))"></div>
    {''.join(f'<div class="abs" style="left:{x}px;top:{y}px;width:{w}px;height:2px;border-radius:2px;background:rgba(255,255,255,.22)"></div>' for x, y, w in ((20, 90, 60), (110, 100, 80), (40, 112, 50), (150, 84, 70)))}
    <div class="abs gl" style="left:10px;bottom:10px;border-radius:14px;padding:5px 10px;font-size:11px;font-weight:700;display:flex;gap:5px;align-items:center;color:#18A957">{ic("check", 13, 3)}<span style="color:#0D2033">Verified · 3 reports merged</span></div>
  </div>
  <div class="gl" style="margin:10px 12px 0;border-radius:24px;padding:12px 14px;display:flex;gap:12px;align-items:center">
    <div style="background:linear-gradient(180deg,#F3F8FC,#DDEBF6);border-radius:18px;padding:6px 4px 0">{body(150, "#B9CCDB", "rgba(11,91,181,.82)", "#5E7487", 56, 122)}</div>
    <div><div class="muted" style="font-size:11px;font-weight:700;letter-spacing:.06em">DEPTH</div>
      <div style="font-size:27px;font-weight:800;line-height:1;color:#0B5BB5">Knee-deep</div>
      <div class="ta muted" style="font-size:11px;margin-top:3px">{TA["knee"]}</div>
      <div style="font-size:11px;margin-top:6px">Against a tyre · <b>82%</b> sure</div></div>
  </div>
  <div class="gl" style="margin:10px 12px 0;border-radius:22px;padding:12px 10px">{veh_row("gl", "gl", 42)}</div>
  <div style="margin:10px 12px 0;border-radius:18px;padding:10px 12px;display:flex;gap:10px;align-items:center;background:linear-gradient(120deg,#FF6A55,#E0322A);color:#fff">
    {ic("warn", 20)}<div><div style="font-weight:700;font-size:13px">Open manhole spotted</div><div style="font-size:11px;opacity:.9">Routes now keep 30 m clear</div></div></div>
  <div class="gl" style="margin:10px 12px 0;border-radius:20px;padding:11px 14px">
    <div style="font-size:12.5px;font-weight:700">You taught the map</div>
    
    <div style="display:flex;align-items:center;gap:8px;font-size:12px;font-weight:800"><span class="muted" style="text-decoration:line-through">68 mm</span>
      <div style="flex:1;height:6px;border-radius:3px;background:linear-gradient(90deg,#9FB6C9,#1592E6)"></div><span style="color:#1592E6">55 mm</span></div></div>
</div>'''

s1_route = f'''<div class="ph s1" style="background:#E4EFF7">
  <div class="abs" style="inset:0">{map_svg(268, 340, M1, show_route=True)}</div>
  <div style="position:relative">{sb()}</div>
  <div style="position:relative;display:flex;justify-content:space-between;align-items:center;padding:10px 14px 0">
    <div class="c gl">{ic("back", 17)}</div>
    <div class="gl" style="display:flex;gap:4px;padding:4px;border-radius:26px">
      <div class="c blue" style="width:36px;height:36px">{ic("bike", 17)}</div><div class="c" style="width:36px;height:36px">{ic("car", 17)}</div><div class="c" style="width:36px;height:36px">{ic("amb", 17)}</div></div></div>
  <div class="abs gl" style="left:0;right:0;bottom:0;border-radius:30px 30px 0 0;padding:16px 16px 18px;background:rgba(255,255,255,.82)">
    <div style="width:36px;height:4px;border-radius:2px;background:#C3D3E0;margin:-6px auto 12px"></div>
    <div style="display:flex;justify-content:space-between;align-items:baseline"><div style="font-size:24px;font-weight:800">1 min <span class="muted" style="font-size:14px;font-weight:600">· 407 m</span></div><span style="font-size:11px;font-weight:700;color:#18A957">Safe for bikes</span></div>
    <div style="font-size:13px;margin-top:6px;line-height:1.35">Avoids Velachery Main Road, reported knee-deep.</div>
    <div class="ta muted" style="font-size:10.5px;margin-top:3px">{TA["reason"]}</div>
    <div style="display:flex;gap:6px;margin:10px 0 12px"><span class="pill" style="background:#E3EEF8;padding:5px 10px;font-size:11px">1 flooded street avoided</span><span class="pill" style="background:#FDE3DC;color:#C0322A;padding:5px 10px;font-size:11px">1 hazard</span></div>
    <div class="blue" style="border-radius:22px;padding:12px;text-align:center;font-weight:700">Start</div></div>
</div>'''

# ================= S2 DEEP TIDE =================
rain = "".join(f'<span class="abs" style="left:{x}px;top:{y}px;width:1px;height:{l}px;background:rgba(255,255,255,.35);transform:rotate(14deg)"></span>'
               for x, y, l in ((20, 40, 16), (60, 70, 12), (110, 30, 18), (160, 80, 14), (210, 44, 16), (240, 96, 12), (36, 120, 14), (190, 130, 12), (88, 150, 10), (140, 118, 16)))
TIDE = ["#3E78A0", "#2E6690", "#22557F", "#18456E", "#10365E", "#0A2849"]

def tide_row(top, col, icon, name, sub, right, rc, ta=None):
    return f'''<div class="abs" style="left:0;right:0;top:{top}px;padding:0 20px;display:flex;justify-content:space-between;align-items:center">
      <div style="display:flex;gap:10px;align-items:center"><div style="width:34px;height:34px;border-radius:50%;background:rgba(255,255,255,.12);display:grid;place-items:center">{ic(icon, 17)}</div>
      <div><div style="font-weight:600;font-size:14px">{name}</div><div class="muted" style="font-size:11px">{sub}</div></div></div>
      <div style="text-align:right;font-weight:600;font-size:12.5px;white-space:nowrap;color:{rc}">{right}</div></div>'''

s2_home = f'''<div class="ph s2">{rain}{sb("#fff")}
  <div style="text-align:center;letter-spacing:.32em;font-size:12px;font-weight:600;margin-top:12px">NIMBUS</div>
  <div style="text-align:center;margin-top:16px"><div class="muted" style="font-size:11.5px">Replay · Cyclone Michaung · 4 Dec 02:00</div>
    <div style="font-size:24px;font-weight:500;line-height:1.15;margin-top:8px;padding:0 24px">2 of your places<br>need you now</div>
    <div class="ta muted" style="font-size:11px;margin-top:6px">{TA["places"]}</div></div>
  <div class="abs" style="left:0;right:0;top:186px">{waves(TIDE, [0, 66, 132, 198, 264, 330], h=394, amp=11)}</div>
  {tide_row(206, TIDE[0], "office", "Office", "Clear for 6 h", "Low", "#CFE3F0")}
  {tide_row(272, TIDE[1], "school", "Kid's school", "Water near the gate by 05:00", "Watch<br>3 h", "#F2B34A")}
  {tide_row(338, TIDE[2], "home", "Home", "32 mm due · floods at 68 mm", "Likely<br>1h 40m", "#FF7A57")}
  {tide_row(404, TIDE[3], "bike", "Bike parking", "Move it to Vijayanagar 1st Main", "Knee-<br>deep", "#59D8E6")}
  <div class="abs" style="left:0;right:0;bottom:18px;display:flex;justify-content:space-around;padding:0 18px">
    {''.join(f'<div style="text-align:center"><div class="cb" style="{st}">{x}</div><div style="font-size:10.5px;margin-top:7px;color:#CFE3F0">{l}</div></div>' for x, l, st in ((ic("camera", 19), "Report", ""), (ic("route", 19), "Route", ""), (ic("map", 19), "Map", ""), ('<b style="font-size:12px">SOS</b>', "Help", "background:#E8432A;box-shadow:0 0 0 6px rgba(232,67,42,.22)")))}
  </div>
</div>'''

s2_depth = f'''<div class="ph s2" style="background:linear-gradient(180deg,#5F8FAE 0%,#3B6E93 48%)">{rain}{sb("#fff")}
  <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 18px 0"><span>{ic("back", 20)}</span><span style="letter-spacing:.24em;font-size:11px;font-weight:600">YOUR REPORT</span><span class="ta" style="font-weight:600">த</span></div>
  <div style="text-align:center;margin-top:10px"><span style="font-size:11px;padding:4px 10px;border-radius:12px;background:rgba(255,255,255,.14)">Verified · 3 reports merged · 82% sure</span></div>
  <div style="display:flex;justify-content:center;margin-top:8px">{body(158, "#D3E3EE", "rgba(0,0,0,0)", "rgba(255,255,255,.5)", 110, 240, wave=False)}</div>
  <div class="abs" style="left:0;right:0;top:278px">{waves(["#2E6E99", "#225A86", "#174775", "#0F3561", "#0A2849"], [0, 40, 100, 170, 230], h=302, amp=9)}</div>
  <div class="abs" style="left:0;right:0;top:318px;text-align:center"><div style="font-size:38px;font-weight:600;line-height:1">Knee-deep</div><div class="ta" style="font-size:12px;opacity:.85;margin-top:4px">{TA["knee"]}</div></div>
  <div class="abs" style="left:18px;right:18px;top:384px">{veh_row("", "", 44, "#CFE3F0").replace('class=""', 'class="" style="background:rgba(255,255,255,.12)"')}</div>
  <div class="abs" style="left:18px;right:18px;top:470px;display:flex;gap:10px;align-items:center;color:#FF8A70">{ic("warn", 20)}<span style="font-size:12.5px;color:#fff">Open manhole here. Routes keep 30 m clear.</span></div>
  <div class="abs" style="left:18px;right:18px;bottom:22px;font-size:12.5px;line-height:1.4"><span class="t" style="font-weight:600">You taught the map.</span> <span class="muted">Velachery Main Rd now floods at</span> 55 mm <span class="muted">(was 68).</span></div>
</div>'''

s2_route = f'''<div class="ph s2" style="background:#0C2347">
  <div class="abs" style="inset:0">{map_svg(268, 350, M2, show_route=True)}</div>
  <div style="position:relative">{sb("#fff")}</div>
  <div style="position:relative;display:flex;justify-content:center;gap:10px;margin-top:10px">
    {''.join(f'<div class="cb" style="width:40px;height:40px;{"" if a else "background:rgba(255,255,255,.1);box-shadow:none"}">{ic(n, 18)}</div>' for n, a in (("bike", True), ("car", False), ("amb", False)))}</div>
  <div class="abs" style="left:0;right:0;bottom:0">{waves(["#1A4877", "#13386A", "#0A1F44"], [18, 36, 56], h=250, amp=10)}</div>
  <div class="abs" style="left:20px;right:20px;bottom:22px">
    <div style="font-size:30px;font-weight:500">1 min <span class="muted" style="font-size:15px">· 407 m · bike</span></div>
    <div style="font-size:13px;margin-top:8px;line-height:1.4">Avoids Velachery Main Road, reported knee-deep.</div>
    <div class="ta muted" style="font-size:10.5px;margin-top:4px">{TA["reason"]}</div>
    <div style="margin-top:14px;border-radius:24px;padding:12px;text-align:center;font-weight:600;background:#2FA9B8">Start</div></div>
</div>'''

# ================= S3 TIDE GLASS =================
def s3_tile(icon, name, sub, tag, tagbg, tagfg, fill, fillcol, ink="#0B1E31"):
    wv = waves([fillcol], [6], h=int(68 * fill) + 6, amp=4) if fill else ""
    return f'''<div class="gl" style="margin:0 14px 9px;border-radius:20px;height:68px;position:relative;overflow:hidden;color:{ink}">
      <div class="abs" style="left:0;right:0;bottom:0">{wv}</div>
      <div style="position:relative;display:flex;justify-content:space-between;align-items:center;padding:13px 14px">
        <div style="display:flex;gap:10px;align-items:center"><div style="width:36px;height:36px;border-radius:12px;background:rgba(255,255,255,.75);display:grid;place-items:center;color:#0B1E31">{ic(icon, 17)}</div>
        <div><div style="font-weight:700;font-size:14px">{name}</div><div style="font-size:11px;opacity:.8">{sub}</div></div></div>
        <span class="chip" style="background:{tagbg};color:{tagfg}">{tag}</span></div></div>'''

S3W = ["#BFD9EA", "#94C1DF", "#5E9FCF", "#2E7CBA", "#1557A8"]
s3_home = f'''<div class="ph s3">{sb()}
  <div class="abs" style="left:0;right:0;bottom:0">{waves(S3W, [0, 22, 44, 70, 98], h=170, amp=9)}</div>
  <div style="padding:12px 14px 0;display:flex;justify-content:space-between;align-items:center">
    <div class="gl" style="border-radius:20px;padding:6px 11px;font-size:11px;font-weight:700;display:flex;gap:6px;align-items:center"><span style="width:7px;height:7px;border-radius:50%;background:#E8432A;box-shadow:0 0 0 3px rgba(232,67,42,.2)"></span>Replay · 02:00 · 18 mm/h</div>
    <div class="gl ta" style="width:34px;height:34px;border-radius:50%;display:grid;place-items:center;font-weight:600">த</div></div>
  <div style="padding:16px 18px 12px"><div class="muted" style="font-size:12px;font-weight:600">Velachery <span class="ta">· {TA["velachery"]}</span></div>
    <div style="font-size:26px;font-weight:800;letter-spacing:-.02em;line-height:1.05;margin-top:4px">Move your bike<br>in the next 20 min</div></div>
  {s3_tile("bike", "Bike parking", "To Vijayanagar 1st Main Rd", "Knee-deep", "#fff", "#1557A8", 1, "#1557A8", "#fff")}
  {s3_tile("home", "Home", "32 mm due · floods at 68 mm", "Likely · 1h 40m", "#EB5A3C", "#fff", .5, "rgba(235,90,60,.25)")}
  {s3_tile("school", "Kid's school", "Water near the gate by 05:00", "Watch · 3 h", "#F2A93B", "#fff", .25, "rgba(242,169,59,.25)")}
  {s3_tile("office", "Office", "Clear for 6 h", "Low", "#E1EAF1", "#5B7084", 0, "")}
  <div class="abs gl" style="left:14px;right:14px;bottom:16px;border-radius:26px;padding:7px;display:flex;justify-content:space-between;align-items:center">
    <div style="width:44px;height:44px;border-radius:50%;background:#0B1E31;color:#fff;display:grid;place-items:center">{ic("home", 18)}</div>
    <div style="display:grid;place-items:center;width:44px">{ic("map", 19)}</div><div style="display:grid;place-items:center;width:44px">{ic("camera", 19)}</div><div style="display:grid;place-items:center;width:44px">{ic("route", 19)}</div>
    <div style="width:44px;height:44px;border-radius:50%;background:#E8432A;color:#fff;display:grid;place-items:center;font-weight:800;font-size:11px">SOS</div></div>
</div>'''

s3_depth = f'''<div class="ph s3">{sb()}
  <div class="abs" style="left:0;right:0;top:272px">{waves(S3W, [0, 22, 46, 80, 114], h=330, amp=9)}</div>
  <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 14px 0"><div class="gl" style="width:34px;height:34px;border-radius:50%;display:grid;place-items:center">{ic("back", 17)}</div><span style="font-weight:700">Your report</span><span class="chip" style="background:#DDF3E6;color:#13894A">Verified</span></div>
  <div style="padding:14px 18px 0;display:flex;gap:6px;align-items:flex-end">
    <div><div class="muted" style="font-size:11px;font-weight:700;letter-spacing:.08em">VELACHERY MAIN RD</div>
      <div style="font-size:36px;font-weight:800;letter-spacing:-.02em;line-height:1;color:#1557A8;margin-top:4px">Knee-<br>deep</div>
      <div class="ta muted" style="font-size:11px;margin-top:6px">{TA["knee"]}</div>
      <div style="font-size:11.5px;margin-top:8px">Against a tyre · <b>82%</b> sure<br>3 reports merged</div></div>
    <div style="margin-left:auto">{body(160, "#9FB6C9", "rgba(0,0,0,0)", "#7B90A3", 84, 184, wave=False)}</div></div>
  <div class="abs gl" style="left:14px;right:14px;top:302px;border-radius:22px;padding:12px 8px">{veh_row("", "", 42).replace('class=""', 'class="" style="background:rgba(255,255,255,.8)"')}</div>
  <div class="abs" style="left:14px;right:14px;top:404px;border-radius:18px;padding:10px 12px;display:flex;gap:10px;align-items:center;background:#E8432A;color:#fff">{ic("warn", 19)}<div style="font-size:12px"><b>Open manhole.</b> Routes keep 30 m clear.</div></div>
  <div class="abs gl" style="left:14px;right:14px;bottom:16px;border-radius:20px;padding:11px 14px">
    <div style="font-size:12.5px;font-weight:800">You taught the map</div>
    <div style="display:flex;align-items:center;gap:8px;font-size:12px;font-weight:800;margin-top:7px"><span class="muted" style="text-decoration:line-through">68 mm</span>
      <div style="flex:1;height:6px;border-radius:3px;background:linear-gradient(90deg,#A9BCCB,#1557A8)"></div><span style="color:#1557A8">55 mm</span></div>
    <div class="muted" style="font-size:10.5px;margin-top:5px">This street now floods sooner than terrain alone said.</div></div>
</div>'''

s3_route = f'''<div class="ph s3" style="background:#EEF4F8">
  <div class="abs" style="inset:0">{map_svg(268, 360, M3, show_route=True)}</div>
  <div style="position:relative">{sb()}</div>
  <div class="abs gl" style="left:14px;right:14px;top:40px;border-radius:20px;padding:10px 12px;font-size:12px">
    <div style="display:flex;gap:8px;align-items:center"><span style="width:8px;height:8px;border-radius:50%;background:#0E7BD8"></span>Home</div>
    <div style="height:1px;background:#E1EAF1;margin:7px 0 7px 16px"></div>
    <div style="display:flex;gap:8px;align-items:center"><span style="width:8px;height:8px;border-radius:2px;background:#0B1E31"></span>Office</div></div>
  <div class="abs" style="left:0;right:0;bottom:0">{waves(S3W[2:], [0, 16, 34], h=230, amp=8)}</div>
  <div class="abs gl" style="left:12px;right:12px;bottom:14px;border-radius:26px;padding:14px">
    <div style="display:flex;gap:6px;margin-bottom:10px">{''.join(f'<span class="chip" style="display:flex;gap:5px;align-items:center;{"background:#0B1E31;color:#fff" if a else "background:#E9F0F5"}">{ic(n, 14)}{l}</span>' for n, l, a in (("bike", "Bike", True), ("car", "Car", False), ("amb", "Ambulance", False)))}</div>
    <div style="font-size:24px;font-weight:800">1 min <span class="muted" style="font-size:13px;font-weight:600">· 407 m</span></div>
    <div style="font-size:12.5px;margin-top:4px;line-height:1.35">Avoids Velachery Main Road, reported knee-deep.</div>
    <div class="ta muted" style="font-size:10px;margin-top:3px">{TA["reason"]}</div>
    <div style="margin-top:10px;border-radius:20px;padding:11px;text-align:center;font-weight:800;background:#0B1E31;color:#fff">Start</div></div>
</div>'''


def section(choice, title, why, phones, caps):
    cells = "".join(f'<div>{p}<div class="cap">{c}</div></div>' for p, c in zip(phones, caps))
    return f'<div class="st card" data-choice="{choice}" onclick="toggleSelect(this)"><h3>{title}</h3><p class="why">{why}</p><div class="row3">{cells}</div></div>'


caps = ["Home: your places", "Photo becomes a Reading", "Safe route for a bike"]
html = CSS + '''
<h2>Three styles from your two references</h2>
<p class="subtitle">Each style shows three screens: home, a photo turned into a depth reading, and a bike detour. Maps are the real Velachery streets from our fixtures. The data is the Michaung scene. Click the style you want, or tell me what to steal from each.</p>
''' + section("s1-glacier-glass", "1 · Glacier glass",
              "Straight from your first reference. Icy blue, frosted round buttons, a hero storm card with rings for rain, wet ground and tide, and the flooded place as a big card full of water. Premium and friendly.",
              [s1_home, s1_depth, s1_route], caps) + section(
    "s2-deep-tide", "2 · Deep tide",
    "Straight from your second reference. The whole app is the sea. On home, each of your places sits on a wave layer, and the deeper it is, the worse it is. The bike parking is at the bottom. Cinematic and dark, and it looks incredible on video.",
    [s2_home, s2_depth, s2_route], caps) + section(
    "s3-tide-glass", "3 · Tide glass (both together)",
    "Light glass cards floating over layered waves. The waves rise as the storm gets worse, and each card fills with water to its own risk level. The headline tells you what to do, not just what's happening.",
    [s3_home, s3_depth, s3_route], caps) + '''
<p style="font-size:13.5px;opacity:.8;margin-top:6px;line-height:1.5"><b>Kept in all three:</b> predicted risk is warm (amber, then red) and only observed water is blue. Tamil is on every screen, and the த button switches the whole app. The icons are drawn for this app, with no emoji. The "68 → 55 mm" learning number is illustrative, because the real nudge comes from the risk engine.</p>
'''
open(OUT, "w").write(html)
print("ok", len(html))
