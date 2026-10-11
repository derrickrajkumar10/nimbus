"""Draw the README's animated cards as self-contained SVGs.

Standard library only. Colours are the console's "Deep tide" tokens, fonts are the
app's Outfit and Noto Sans Tamil (embedded, so every viewer sees the same type), and
the storm chart is the archived Michaung rain in engines/risk/michaung_rain.json.

    python docs/readme/build.py      # rewrites docs/readme/*.svg

Every animation stops under prefers-reduced-motion.
"""

import base64
import json
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FONTS = ROOT / "app" / "assets" / "fonts"

DEEP, PANEL, RAISE = "#0a1f44", "#0d2650", "#12305e"
TEAL, WATER, TEXT = "#4fd1d9", "#59d8e6", "#ffffff"
MUTED, FAINT, LOWC = "#a9c6db", "#6f93b3", "#cfe3f0"
WATCH, LIKELY, SOS = "#f2b34a", "#ff7a57", "#e8432a"


def _font(name: str, family: str, weight: int) -> str:
    data = base64.b64encode((FONTS / name).read_bytes()).decode()
    return f"@font-face{{font-family:'{family}';font-weight:{weight};src:url(data:font/ttf;base64,{data}) format('truetype')}}"


OUTFIT = _font("Outfit-SemiBold.ttf", "Outfit", 600) + _font("Outfit-Regular.ttf", "Outfit", 400)
TAMIL = _font("NotoSansTamil-Medium.ttf", "Tamil", 500)

BASE_CSS = f"""
text{{font-family:'Outfit','Segoe UI',Helvetica,Arial,sans-serif;fill:{TEXT}}}
.ta{{font-family:'Tamil','Outfit',sans-serif}}
.muted{{fill:{MUTED}}} .faint{{fill:{FAINT}}} .teal{{fill:{TEAL}}}
.up{{opacity:0;animation:up .9s cubic-bezier(.2,.7,.2,1) forwards}}
@keyframes up{{from{{opacity:0;transform:translateY(14px)}}to{{opacity:1;transform:none}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}} .up{{opacity:1}}}}
"""


def svg(name: str, w: int, h: int, body: str, css: str = "", label: str = "", tamil: bool = False, fonts: bool = True) -> None:
    fonts = (OUTFIT if fonts else "") + (TAMIL if tamil else "")
    out = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">'
        f"<title>{label}</title><style>{fonts}{BASE_CSS}{css}</style>{body}</svg>"
    )
    (HERE / f"{name}.svg").write_text(out)


def card(w: int, h: int, fill: str = PANEL, stroke: str = RAISE, rx: int = 18) -> str:
    return f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'


def wrap(text: str, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line] if line else lines


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def waves_mark(x: float, y: float, s: float = 1.0, colour: str = TEAL) -> str:
    """The console's three-wave NIMBUS mark."""
    paths = "".join(
        f'<path d="M0 {i * 7} q5 -5 10 0 t10 0 t10 0" fill="none" stroke="{colour}" stroke-width="2.6" stroke-linecap="round"/>'
        for i in range(3)
    )
    return f'<g transform="translate({x} {y}) scale({s})">{paths}</g>'


# --- hero ----------------------------------------------------------------------


def hero() -> None:
    w, h = 900, 360
    rain = []
    for i in range(70):
        x = (i * 37.3) % w
        dur = 0.7 + (i * 7 % 10) / 14
        delay = -(i * 0.13 % 1.6)
        length = 10 + i % 4 * 4
        op = 0.25 + (i % 5) * 0.09
        rain.append(
            f'<line x1="{x:.1f}" y1="-20" x2="{x - 3:.1f}" y2="{-20 + length}" stroke="{LOWC}" stroke-opacity="{op:.2f}" '
            f'stroke-width="1.4" stroke-linecap="round" style="animation:fall {dur:.2f}s linear {delay:.2f}s infinite"/>'
        )
    wave = lambda amp, y: f"M0 {y} " + " ".join(  # noqa: E731
        f"Q{x + 37.5} {y - amp} {x + 75} {y} T{x + 150} {y}" for x in range(0, w * 2, 150)
    ) + f" V{h} H0 Z"
    body = f"""
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#061634"/><stop offset="1" stop-color="{PANEL}"/></linearGradient>
  <linearGradient id="w1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{WATER}" stop-opacity=".55"/><stop offset="1" stop-color="{TEAL}" stop-opacity=".15"/></linearGradient>
  <linearGradient id="w2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2fa9b8" stop-opacity=".7"/><stop offset="1" stop-color="{DEEP}" stop-opacity=".9"/></linearGradient>
  <clipPath id="c"><rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="22"/></clipPath>
</defs>
<g clip-path="url(#c)">
  <rect width="{w}" height="{h}" fill="url(#sky)"/>
  <g class="rain">{''.join(rain)}</g>
  <g class="rise">
    <path class="wv a" d="{wave(9, 300)}" fill="url(#w1)"/>
    <path class="wv b" d="{wave(7, 314)}" fill="url(#w2)"/>
  </g>
</g>
<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="22" fill="none" stroke="{RAISE}" stroke-width="2"/>
<g class="up" style="animation-delay:.1s">
  <rect x="60" y="48" width="292" height="30" rx="15" fill="{RAISE}" stroke="#1d4a82"/>
  <circle class="live" cx="80" cy="63" r="5" fill="{LIKELY}"/>
  <text x="94" y="68" font-size="13" font-weight="600" letter-spacing="1.5" fill="{LOWC}">REPLAY · CYCLONE MICHAUNG · 2023</text>
</g>
{waves_mark(62, 116, 1.5).replace('<g ', '<g class="up" style="animation-delay:.25s" ', 1)}
<text class="up" style="animation-delay:.25s" x="118" y="140" font-size="58" font-weight="600" letter-spacing="10">NIMBUS</text>
<text class="up" style="animation-delay:.45s" x="62" y="186" font-size="22" font-weight="400" fill="{LOWC}">Street-level flood warnings and response for Chennai</text>
<text class="up ta" style="animation-delay:.6s" x="62" y="220" font-size="18" font-weight="500" fill="{WATER}">ஒவ்வொரு தெருவுக்கும் வெள்ள எச்சரிக்கை</text>
<g class="up" style="animation-delay:.8s" font-size="13" font-weight="600">
  <rect x="62" y="244" width="150" height="28" rx="14" fill="none" stroke="{TEAL}"/><text x="137" y="263" text-anchor="middle" class="teal">Heat &amp; Water track</text>
  <rect x="222" y="244" width="196" height="28" rx="14" fill="none" stroke="{FAINT}"/><text x="320" y="263" text-anchor="middle" class="muted">Strands Agents · Cedar</text>
  <rect x="428" y="244" width="300" height="28" rx="14" fill="none" stroke="{FAINT}"/><text x="578" y="263" text-anchor="middle" class="muted">Lambda · EventBridge · DynamoDB · CDK</text>
</g>
"""
    css = f"""
@keyframes fall{{from{{transform:translate(0,0)}}to{{transform:translate(-40px,{h + 40}px)}}}}
@keyframes drift{{from{{transform:translateX(0)}}to{{transform:translateX(-150px)}}}}
@keyframes rise{{0%,100%{{transform:translateY(16px)}}50%{{transform:translateY(-6px)}}}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:.2}}}}
.wv.a{{animation:drift 7s linear infinite}} .wv.b{{animation:drift 4.5s linear infinite reverse}}
.rise{{animation:rise 9s ease-in-out infinite}}
.live{{animation:blink 1.4s ease-in-out infinite}}
"""
    svg("hero", w, h, body, css, "NIMBUS: street-level flood warnings and response for Chennai", tamil=True)


# --- stats ---------------------------------------------------------------------


def stats() -> None:
    w, h = 900, 160
    items = [
        ("21", "street segments", "scored every 15 storm-minutes", TEAL),
        ("34 h", "early warning", "first watch → first likely", WATCH),
        ("3", "agents on AWS", "every action checked by Cedar", LIKELY),
        ("≈ 1¢", "to build and run", "pay-per-use, $0 when idle", WATER),
    ]
    cw, gap = 210, 20
    body = []
    for i, (big, title, sub, colour) in enumerate(items):
        x = i * (cw + gap)
        body.append(
            f'<g class="up" style="animation-delay:{0.15 * i:.2f}s"><g transform="translate({x} 0)">{card(cw, h)}'
            f'<rect x="22" y="24" width="34" height="4" rx="2" fill="{colour}"/>'
            f'<text x="22" y="76" font-size="40" font-weight="600" fill="{colour}">{big}</text>'
            f'<text x="22" y="106" font-size="16" font-weight="600">{title}</text>'
            f'<text x="22" y="130" font-size="13" class="muted">{esc(sub)}</text></g></g>'
        )
    svg("stats", w, h, "".join(body), label="21 street segments; 34 hours early warning; 3 agents; about 1 cent on AWS")


# --- storm timeline ------------------------------------------------------------


def storm() -> None:
    w, h = 900, 330
    rain = json.loads((ROOT / "engines" / "risk" / "michaung_rain.json").read_text())["hourly"]
    start = datetime.fromisoformat("2023-12-02T12:00:00+05:30")
    hours = 60
    values = [rain.get((start + timedelta(hours=i)).isoformat(), 0.0) for i in range(hours)]
    peak = max(values) or 1
    x0, x1, base, top = 40, 860, 240, 104
    step = (x1 - x0) / hours

    def x_at(t: str) -> float:
        dt = datetime.fromisoformat(t) - start
        return x0 + dt.total_seconds() / 3600 * step

    bars = []
    for i, v in enumerate(values):
        bh = (base - top) * v / peak
        bars.append(
            f'<rect class="bar" x="{x0 + i * step + 1:.1f}" y="{base - bh:.1f}" width="{step - 3:.1f}" height="{bh:.1f}" rx="2" '
            f'fill="{WATER}" fill-opacity="{0.35 + 0.65 * v / peak:.2f}" style="animation-delay:{0.6 + i * 0.025:.3f}s;transform-origin:0 {base}px"/>'
        )
    ticks = []
    for d in range(0, hours + 1, 12):
        t = start + timedelta(hours=d)
        x = x0 + d * step
        ticks.append(
            f'<line x1="{x:.1f}" y1="{base}" x2="{x:.1f}" y2="{base + 6}" stroke="{FAINT}"/>'
            f'<text x="{x:.1f}" y="{base + 24}" font-size="12" text-anchor="{"end" if d == hours else "start" if d == 0 else "middle"}" class="faint">{t:%d %b %H:%M}</text>'
        )
    marks = [
        ("2023-12-02T17:45:00+05:30", WATCH, "First street on watch", "2 Dec 17:45"),
        ("2023-12-04T03:45:00+05:30", LIKELY, "First likely · Pump 3 proposed", "4 Dec 03:45"),
        ("2023-12-04T07:45:00+05:30", SOS, "All 21 segments likely", "4 Dec 07:45"),
    ]
    flags, legend = [], []
    lx = 30
    for i, (t, colour, label, when) in enumerate(marks):
        x = x_at(t)
        y = top - 6 + i * 22
        flags.append(
            f'<g class="up" style="animation-delay:{2.2 + i * 0.35:.2f}s">'
            f'<line x1="{x:.1f}" y1="{y + 10}" x2="{x:.1f}" y2="{base}" stroke="{colour}" stroke-width="2" stroke-dasharray="4 4"/>'
            f'<circle cx="{x:.1f}" cy="{y}" r="10" fill="{DEEP}" stroke="{colour}" stroke-width="2"/>'
            f'<text x="{x:.1f}" y="{y + 4.5}" font-size="12" font-weight="600" text-anchor="middle" fill="{colour}">{i + 1}</text></g>'
        )
        text = f"{when} · {label}"
        legend.append(
            f'<g class="up" style="animation-delay:{2.2 + i * 0.35:.2f}s"><circle cx="{lx + 8}" cy="{base + 50}" r="8" fill="none" stroke="{colour}" stroke-width="1.6"/>'
            f'<text x="{lx + 8}" y="{base + 54}" font-size="10.5" font-weight="600" text-anchor="middle" fill="{colour}">{i + 1}</text>'
            f'<text x="{lx + 22}" y="{base + 55}" font-size="12.5" class="muted">{text}</text></g>'
        )
        lx += 22 + len(text) * 6.6 + 24
    body = f"""
{card(w, h)}
<text class="up" x="30" y="44" font-size="20" font-weight="600">The storm, replayed through the live system</text>
<text class="up muted" style="animation-delay:.15s" x="30" y="68" font-size="13">Hourly rain over Velachery, 2–5 Dec 2023 (Open-Meteo archive, peak {peak:.1f} mm/h). The Sentinel scores every street each 15 storm-minutes.</text>
<line x1="{x0}" y1="{base}" x2="{x1}" y2="{base}" stroke="{FAINT}" stroke-opacity=".6"/>
{''.join(bars)}{''.join(ticks)}{''.join(flags)}{''.join(legend)}
<line class="sweep" x1="{x0}" y1="{top - 10}" x2="{x0}" y2="{base}" stroke="{TEXT}" stroke-opacity=".7" stroke-width="1.5"/>
<text x="870" y="44" font-size="12" text-anchor="end" class="faint">bars: rain, mm/h · times IST</text>
"""
    css = f"""
.bar{{transform:scaleY(0);animation:grow .5s ease-out forwards}}
@keyframes grow{{to{{transform:scaleY(1)}}}}
.sweep{{animation:sweep 9s linear 1s infinite}}
@keyframes sweep{{from{{transform:translateX(0)}}to{{transform:translateX({x1 - x0}px)}}}}
@media (prefers-reduced-motion:reduce){{.bar{{transform:none}}}}
"""
    svg("storm", w, h, body, css, "Michaung rain over Velachery with the first watch, first likely and all-likely moments")


# --- architecture --------------------------------------------------------------


def flow() -> None:
    w, h = 900, 430
    body = [card(w, h)]
    body.append(f'<text x="30" y="44" font-size="20" font-weight="600">How it works</text>')
    body.append(f'<text x="30" y="68" font-size="13" class="muted">Agents never call each other. They react to events on one EventBridge bus, so a past storm replays through the live system.</text>')

    def node(x, y, w_, h_, title, sub, colour, delay, badge=""):
        b = (
            f'<rect x="{x + w_ - 74}" y="{y - 11}" width="68" height="22" rx="11" fill="{DEEP}" stroke="{WATCH}"/>'
            f'<text x="{x + w_ - 40}" y="{y + 4}" font-size="11" font-weight="600" text-anchor="middle" fill="{WATCH}">{badge}</text>'
            if badge else ""
        )
        return (
            f'<g class="up" style="animation-delay:{delay}s"><rect x="{x}" y="{y}" width="{w_}" height="{h_}" rx="14" fill="{RAISE}" stroke="{colour}" stroke-width="1.6"/>'
            f'<text x="{x + 16}" y="{y + 28}" font-size="15" font-weight="600">{title}</text>'
            f'<text x="{x + 16}" y="{y + 48}" font-size="12" class="muted">{esc(sub)}</text>{b}</g>'
        )

    # bus
    body.append(
        f'<g class="up" style="animation-delay:.2s"><rect x="30" y="196" width="840" height="40" rx="20" fill="{DEEP}" stroke="{TEAL}" stroke-width="1.6"/>'
        f'<text x="450" y="221" font-size="14" font-weight="600" text-anchor="middle" class="teal">Amazon EventBridge · bus “nimbus” · 7-day archive</text></g>'
    )
    body.append(node(30, 96, 180, 64, "Replay Driver", "plays the storm as clock.tick", FAINT, 0.3))
    body.append(node(240, 96, 190, 64, "Sentinel · Lambda", "risk per street → risk.changed", TEAL, 0.45))
    body.append(node(450, 96, 200, 64, "Herald · Lambda", "EN + TA alerts to subscribers", WATCH, 0.6, "Cedar"))
    body.append(node(670, 96, 200, 64, "Dispatcher · Lambda", "pump → street Work Orders", LIKELY, 0.75, "Cedar"))
    body.append(node(30, 272, 250, 64, "Projector · Lambda", "events → tables, one writer each", FAINT, 0.9))
    body.append(node(310, 272, 250, 64, "Amazon DynamoDB", "16 tables, every row keyed by run_id", TEAL, 1.0))
    body.append(node(590, 272, 280, 64, "Amazon API Gateway", "console API · citizen API, throttled", WATER, 1.1))
    body.append(
        f'<g class="up" style="animation-delay:1.3s"><rect x="590" y="352" width="280" height="56" rx="14" fill="{DEEP}" stroke="{TEAL}" stroke-dasharray="5 4"/>'
        f'<text x="610" y="378" font-size="15" font-weight="600">Ward officer</text>'
        f'<text x="610" y="396" font-size="12" class="muted">approves every Proposal</text>'
        f'<rect class="pulse" x="788" y="364" width="66" height="30" rx="8" fill="#2fa9b8"/>'
        f'<text x="821" y="384" font-size="13" font-weight="600" text-anchor="middle">Approve</text></g>'
    )
    # connectors
    links = [
        ("M120 160 V196", FAINT), ("M335 160 V196", TEAL), ("M550 160 V196", WATCH), ("M770 160 V196", LIKELY),
        ("M155 236 V272", FAINT), ("M280 304 H310", FAINT), ("M560 304 H590", TEAL), ("M730 336 V352", WATER),
    ]
    for d, colour in links:
        body.append(f'<path d="{d}" stroke="{colour}" stroke-opacity=".55" stroke-width="2" fill="none"/>')
    # moving events (SMIL, runs in the README image too)
    packets = [
        ("M120 160 V216 H335 V160", TEAL, "clock.tick", 0.0),
        ("M335 160 V216 H550 V160", WATCH, "risk.changed", 1.2),
        ("M335 160 V216 H770 V160", LIKELY, "risk.changed", 1.6),
        ("M770 160 V216 H155 V272", LIKELY, "proposal.created", 2.6),
        ("M280 304 H310 M560 304 H590", WATER, "", 3.6),
    ]
    for d, colour, label, begin in packets:
        tag = f'<text font-size="10.5" font-weight="600" x="8" y="-8" fill="{colour}">{label}</text>' if label else ""
        body.append(
            f'<g opacity="0"><circle r="5.5" fill="{colour}"/><circle r="10" fill="{colour}" fill-opacity=".25"/>{tag}'
            f'<animateMotion dur="2.4s" begin="{begin}s;{begin + 5}s;{begin + 10}s;{begin + 15}s" path="{d}" fill="freeze"/>'
            f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.1;.85;1" dur="2.4s" begin="{begin}s;{begin + 5}s;{begin + 10}s;{begin + 15}s" fill="freeze"/></g>'
        )
    css = f"""
.pulse{{animation:pulse 1.8s ease-in-out infinite;transform-origin:821px 379px}}
@keyframes pulse{{0%,100%{{transform:scale(1);opacity:1}}50%{{transform:scale(1.06);opacity:.8}}}}
"""
    svg("flow", w, h, "".join(body), css, "Architecture: Replay Driver, EventBridge, Sentinel, Herald, Dispatcher, projector, DynamoDB, API Gateway, ward officer")


# --- agents --------------------------------------------------------------------


def agents() -> None:
    w, h = 286, 230

    def agent(name, colour, role, lines, art, extra_css="", tamil=False):
        body = [card(w, h)]
        body.append(f'<rect x="22" y="24" width="34" height="4" rx="2" fill="{colour}"/>')
        body.append(f'<text x="22" y="58" font-size="22" font-weight="600">{name}</text>')
        body.append(f'<text x="22" y="80" font-size="12.5" fill="{colour}" font-weight="600">{role}</text>')
        for i, line in enumerate(lines):
            body.append(f'<text x="22" y="{128 + i * 20}" font-size="12.5" class="muted">{esc(line)}</text>')
        body.append(art)
        svg(f"agent-{name.lower()}", w, h, "".join(body), extra_css, f"{name}: {role}", tamil=tamil)

    radar = (
        f'<g transform="translate(238 52)"><circle r="28" fill="none" stroke="{TEAL}" stroke-opacity=".35"/>'
        f'<circle r="18" fill="none" stroke="{TEAL}" stroke-opacity=".35"/><circle r="3" fill="{TEAL}"/>'
        f'<path class="beam" d="M0 0 L28 0 A28 28 0 0 0 19.8 -19.8 Z" fill="{TEAL}" fill-opacity=".35"/>'
        f'<circle class="blip" cx="12" cy="-16" r="3.5" fill="{LIKELY}"/></g>'
    )
    agent(
        "Sentinel", TEAL, "Predicts, street by street",
        ["Scores 21 segments every tick:", "72 h of rain + next 3 h vs each", "street's flood threshold."],
        radar,
        f".beam{{animation:spin 3s linear infinite}} @keyframes spin{{to{{transform:rotate(360deg)}}}}"
        f".blip{{animation:ping 3s ease-out infinite}} @keyframes ping{{0%,60%{{opacity:0}}70%{{opacity:1}}100%{{opacity:0}}}}",
    )
    bubble = (
        f'<g transform="translate(184 18)"><rect width="84" height="40" rx="12" fill="{RAISE}" stroke="{WATCH}"/>'
        f'<path d="M18 40 l-6 9 l14 -9" fill="{RAISE}" stroke="{WATCH}"/>'
        f'<text class="en" x="42" y="26" font-size="14" font-weight="600" text-anchor="middle" fill="{WATCH}">Move bike</text>'
        f'<text class="ta tam" x="42" y="26" font-size="12" text-anchor="middle" fill="{WATCH}">நகர்த்துங்கள்</text></g>'
    )
    agent(
        "Herald", WATCH, "Warns, in English and Tamil",
        ["Fixed templates: no invented facts.", "Alert >100 people? Cedar holds it", "for an officer's approval."],
        bubble,
        ".en{animation:swap 4s infinite} .tam{animation:swap 4s 2s infinite;opacity:0}"
        "@keyframes swap{0%,45%{opacity:1}50%,95%{opacity:0}100%{opacity:1}}",
        tamil=True,
    )
    pump = (
        f'<g transform="translate(166 24)"><path d="M0 26 C20 10 40 34 60 18 S90 14 96 22" fill="none" stroke="{FAINT}" stroke-dasharray="4 4"/>'
        f'<circle cx="96" cy="22" r="7" fill="{LIKELY}" fill-opacity=".3" stroke="{LIKELY}"/>'
        f'<g class="truck"><rect x="-10" y="-8" width="20" height="13" rx="3" fill="{LIKELY}"/><circle cx="-5" cy="7" r="3" fill="{TEXT}"/><circle cx="5" cy="7" r="3" fill="{TEXT}"/>'
        f'<animateMotion dur="3.2s" repeatCount="indefinite" path="M0 26 C20 10 40 34 60 18 S90 14 96 22"/></g></g>'
    )
    agent(
        "Dispatcher", LIKELY, "Sends pumps, after approval",
        ["Ranks free pumps by impact over", "travel time; proposes Work Orders.", "Crews move only when approved."],
        pump,
    )


# --- the approval moment -------------------------------------------------------


def approve() -> None:
    w, h = 900, 250
    body = f"""
{card(w, h)}
<text class="up" x="30" y="44" font-size="20" font-weight="600">AI proposes. A human decides.</text>
<text class="up muted" style="animation-delay:.15s" x="30" y="68" font-size="13">From the live replay in AWS: the Dispatcher's first Work Order, and what happens when the officer approves it.</text>
<g class="up" style="animation-delay:.4s">
  <rect x="30" y="88" width="520" height="138" rx="16" fill="{RAISE}" stroke="{TEAL}" stroke-width="1.6"/>
  <text x="52" y="116" font-size="12" font-weight="600" letter-spacing="1.2" class="faint">WORK ORDER</text>
  <text x="528" y="116" font-size="12" text-anchor="end" class="faint">Dispatcher · 4 Dec 03:45</text>
  <text x="52" y="144" font-size="18" font-weight="600">Send Pump 3 to Vijayanagar 1st Main Road</text>
  <text x="52" y="168" font-size="13" class="muted">likely · about 47 buildings nearby · 2 min away</text>
  <text x="52" y="188" font-size="12" class="faint">Score 6.9 = impact 47 ÷ (1.8 min travel + 5 min to set off)</text>
  <rect class="press" x="400" y="186" width="128" height="30" rx="9" fill="#2fa9b8"/>
  <text x="464" y="206" font-size="14" font-weight="600" text-anchor="middle">Approve</text>
</g>
<g class="cursor" transform="translate(470 200)"><path d="M0 0 L0 18 L5 13 L9 22 L12 21 L8 12 L15 12 Z" fill="{TEXT}" stroke="{DEEP}" stroke-width="1.2"/></g>
<g class="toast">
  <rect x="580" y="96" width="290" height="56" rx="14" fill="{DEEP}" stroke="{WATCH}"/>
  <text x="600" y="120" font-size="12" font-weight="600" fill="{WATCH}">Cedar · DispatchCrew</text>
  <text x="600" y="140" font-size="13" class="muted">allowed: officer approved</text>
</g>
<g class="toast2">
  <rect x="580" y="164" width="290" height="62" rx="14" fill="{DEEP}" stroke="{TEAL}"/>
  <circle cx="602" cy="195" r="6" fill="{TEAL}"/>
  <text x="618" y="190" font-size="14" font-weight="600">Pump 3 en route</text>
  <text x="618" y="209" font-size="12.5" class="muted">to Vijayanagar 1st Main Road</text>
</g>
"""
    css = """
.cursor{animation:move 6s ease-in-out infinite}
@keyframes move{0%{transform:translate(700px,60px)}30%,45%{transform:translate(470px,200px)}100%{transform:translate(470px,200px)}}
.press{animation:press 6s infinite;transform-origin:464px 201px}
@keyframes press{0%,33%{transform:scale(1)}36%{transform:scale(.92)}40%,100%{transform:scale(1)}}
.toast{opacity:0;animation:t1 6s infinite} .toast2{opacity:0;animation:t2 6s infinite}
@keyframes t1{0%,40%{opacity:0;transform:translateX(16px)}48%,92%{opacity:1;transform:none}100%{opacity:0}}
@keyframes t2{0%,52%{opacity:0;transform:translateX(16px)}60%,92%{opacity:1;transform:none}100%{opacity:0}}
@media (prefers-reduced-motion:reduce){.toast,.toast2{opacity:1}}
"""
    svg("approve", w, h, body, css, "A Work Order: Send Pump 3 to Vijayanagar 1st Main Road; the officer approves; Pump 3 en route")


# --- AWS -----------------------------------------------------------------------


def aws() -> None:
    w, h = 900, 300
    tiles = [
        ("AWS Lambda", "7 functions: 3 agents, projector, 2 APIs, push", TEAL),
        ("Amazon EventBridge", "one bus, a rule per agent and event, archive", TEAL),
        ("Amazon DynamoDB", "16 on-demand tables keyed by run_id", TEAL),
        ("Amazon API Gateway", "console + citizen HTTP APIs, throttled", TEAL),
        ("Amazon S3 · SSM", "photos, shared configuration", WATER),
        ("AWS CDK", "3 stacks, unit-tested, diff before deploy", WATER),
        ("Strands Agents", "agent framework, Nova-ready", WATCH),
        ("Cedar", "guardrails on every outward action", WATCH),
    ]
    body = [card(w, h), f'<text x="30" y="44" font-size="20" font-weight="600">Built on AWS</text>',
            f'<text x="30" y="68" font-size="13" class="muted">Ship It: deployed in us-east-1. Build It: AWS open source (Strands Agents, Cedar).</text>']
    tw, th, gx, gy = 196, 88, 18, 18
    for i, (name, sub, colour) in enumerate(tiles):
        x = 30 + (i % 4) * (tw + gx)
        y = 88 + (i // 4) * (th + gy)
        body.append(
            f'<g class="up" style="animation-delay:{0.1 + i * 0.08:.2f}s"><rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="14" fill="{RAISE}"/>'
            f'<rect class="glow" x="{x}" y="{y}" width="{tw}" height="{th}" rx="14" fill="none" stroke="{colour}" style="animation-delay:{i * 0.4:.1f}s"/>'
            f'<text x="{x + 16}" y="{y + 34}" font-size="15" font-weight="600">{name}</text>'
            + "".join(f'<text x="{x + 16}" y="{y + 56 + j * 16}" font-size="11.5" class="muted">{esc(line)}</text>' for j, line in enumerate(wrap(sub, 30)))
            + "</g>"
        )
    css = ".glow{stroke-opacity:.25;animation:glow 3.2s ease-in-out infinite}@keyframes glow{50%{stroke-opacity:1}}"
    svg("aws", w, h, "".join(body), css, "AWS Lambda, EventBridge, DynamoDB, API Gateway, S3, SSM, CDK, Strands Agents, Cedar")


# --- team ----------------------------------------------------------------------


def team() -> None:
    w, h = 900, 170
    people = [
        ("Vishwa", "Agents · AWS deployment", "Sentinel, Herald, Dispatcher", TEAL),
        ("Varun", "Infrastructure · APIs", "CDK, projector, APIs, push", WATER),
        ("Goutam", "Engines · Storm Replay", "risk engine, dispatch solver", WATCH),
        ("Derrick", "Contracts · Design · Frontend", "domain model, console, app", LIKELY),
    ]
    cw = 210
    body = []
    for i, (name, lane, did, colour) in enumerate(people):
        x = i * (cw + 20)
        body.append(
            f'<g class="up" style="animation-delay:{0.12 * i:.2f}s"><g transform="translate({x} 0)">{card(cw, h)}'
            f'<circle cx="44" cy="52" r="22" fill="{RAISE}" stroke="{colour}" stroke-width="2"/>'
            f'<text x="44" y="59" font-size="20" font-weight="600" text-anchor="middle" fill="{colour}">{name[0]}</text>'
            f'<text x="78" y="58" font-size="18" font-weight="600">{name}</text>'
            f'<text x="22" y="104" font-size="12.5" font-weight="600" fill="{colour}">{esc(lane)}</text>'
            f'<text x="22" y="126" font-size="12" class="muted">{esc(did)}</text></g></g>'
        )
    svg("team", w, h, "".join(body), label="Team: Vishwa, Varun, Goutam, Derrick")


def footer() -> None:
    w, h = 900, 70
    wave = lambda y, amp: f"M0 {y} " + " ".join(f"Q{x + 37.5} {y - amp} {x + 75} {y} T{x + 150} {y}" for x in range(0, w * 2, 150)) + f" V{h} H0 Z"  # noqa: E731
    body = (
        f'<path class="f1" d="{wave(30, 8)}" fill="{TEAL}" fill-opacity=".25"/>'
        f'<path class="f2" d="{wave(40, 6)}" fill="{PANEL}"/>'
    )
    css = ".f1{animation:d 8s linear infinite}.f2{animation:d 5s linear infinite reverse}@keyframes d{to{transform:translateX(-150px)}}"
    svg("footer", w, h, body, css, "", fonts=False)


if __name__ == "__main__":
    for draw in (hero, stats, storm, flow, agents, approve, aws, team, footer):
        draw()
    print("\n".join(f"{p.name} {p.stat().st_size // 1024} KB" for p in sorted(HERE.glob("*.svg"))))
