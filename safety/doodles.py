"""Hand-drawn doodles for Making Human Safe, drawn in code as inline SVG.

Style: near-black ink lines with a slight wobble (SVG turbulence filter), soft wash fills, handwritten
labels (Caveat font, loaded by the page). Every doodle teaches one thing; nothing graphic, no victims.
The recurring cast: Amma (waits at home), Bro (takes risks), Meera (solo traveller), Dadaji (elderly),
Chhotu (child), and Palm (the open-hand guide who says "wait").

Each public function returns an <svg> string with a written description (aria-label + <title>).
"""

import re

INK = "#1d2129"
SEA, SAND, LEAF, WARN, SKY, PAPER, SUN, ROSE, LILAC = ("#cfe3fb", "#fbe7b5", "#d4efe2", "#e34948", "#eef5fe",
                                                        "#ffffff", "#ffd36b", "#fde2e2", "#e6e0f8")

WOBBLE = ('<defs><filter id="wob" x="-5%" y="-5%" width="110%" height="110%">'
          '<feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="2" seed="7"/>'
          '<feDisplacementMap in="SourceGraphic" scale="2.4"/></filter></defs>')


def svg(w, h, label, inner, text=""):
    """inner = wobbly drawing; text = labels drawn without wobble so they stay readable."""
    return (f'<svg class="doodle" viewBox="0 0 {w} {h}" role="img" aria-label="{label}"><title>{label}</title>{WOBBLE}'
            f'<g filter="url(#wob)">{inner}</g>{text}</svg>')


def p(d, fill="none", w=2.4, stroke=INK, extra=""):
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'


def c(x, y, r, fill="none", w=2.4):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{INK}" stroke-width="{w}"/>'


def dot(x, y, r=1.8):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{INK}"/>'


READABLE = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif"


def t(x, y, s, size=20, weight=400, anchor="start", color=INK, hand=None):
    """Text inside drawings. Handwriting only for big, short labels (size 22+ and under 30 characters);
    everything people must read uses a plain upright font, slightly smaller so it fits the same space."""
    plain_len = len(re.sub(r"<[^>]+>|&[a-z#0-9]+;", "x", str(s)))
    use_hand = hand if hand is not None else (size >= 22 and plain_len <= 30)
    if use_hand:
        return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
                f'style="fill:{color}">{s}</text>')
    return (f'<text x="{x}" y="{y}" font-size="{round(size * 0.8, 1)}" font-weight="{max(weight, 500) if weight >= 700 else 400}" '
            f'text-anchor="{anchor}" style="fill:{color};font-family:{READABLE}">{s}</text>')


def arrow(x1, y1, x2, y2, color=INK, w=2.4):
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    h1 = (x2 - 10 * math.cos(a - 0.45), y2 - 10 * math.sin(a - 0.45))
    h2 = (x2 - 10 * math.cos(a + 0.45), y2 - 10 * math.sin(a + 0.45))
    return p(f"M{x1},{y1} Q{(x1 + x2) / 2 + (y2 - y1) * 0.12},{(y1 + y2) / 2 - (x2 - x1) * 0.12} {x2},{y2} "
             f"M{h1[0]:.1f},{h1[1]:.1f} L{x2},{y2} L{h2[0]:.1f},{h2[1]:.1f}", stroke=color, w=w)


# ---------------------------------------------------------------- the cast
def face(x, y, s, glasses=False):
    out = dot(x - 3.6 * s, y - 1 * s, 1.6 * s) + dot(x + 3.6 * s, y - 1 * s, 1.6 * s)
    out += p(f"M{x - 3.5 * s},{y + 4 * s} Q{x},{y + 7 * s} {x + 3.5 * s},{y + 4 * s}", w=1.6 * s)
    if glasses:
        out += c(x - 4 * s, y - 1 * s, 3.2 * s, w=1.3) + c(x + 4 * s, y - 1 * s, 3.2 * s, w=1.3)
    return out


def person(x, y, who="bro", s=1.0, arms="down", fill=None):
    """A cast member standing with feet at (x, y)."""
    if who == "chhotu":
        s *= 0.68
    col = fill or {"bro": "#9cc3f5", "amma": "#f7a8a8", "meera": "#c7b6f2", "dadaji": "#e8e2d4",
                   "chhotu": SUN}.get(who, "#ddd")
    hx, hy, hr = x, y - 68 * s, 11.5 * s * (1.12 if who == "chhotu" else 1)
    out = ""
    if who == "meera":  # backpack behind
        out += p(f"M{x + 6 * s},{y - 54 * s} h12 v24 h-12 z".replace("h12", f"h{12 * s}").replace("v24", f"v{24 * s}")
                 .replace("h-12", f"h{-12 * s}"), fill="#f0c36b", w=1.8)
    if who == "amma":  # saree: long dress with drape
        out += p(f"M{x - 10 * s},{y - 54 * s} L{x + 10 * s},{y - 54 * s} L{x + 16 * s},{y - 2 * s} L{x - 16 * s},{y - 2 * s} Z", fill=col)
        out += p(f"M{x - 9 * s},{y - 53 * s} L{x + 15 * s},{y - 18 * s}", w=1.6, stroke="#c0392b")
    else:
        out += p(f"M{x - 10 * s},{y - 54 * s} h{20 * s} v{26 * s} h{-20 * s} z", fill=col)
        out += p(f"M{x - 5 * s},{y - 28 * s} L{x - 7 * s},{y} M{x + 5 * s},{y - 28 * s} L{x + 7 * s},{y}")
    # arms
    if arms == "down":
        out += p(f"M{x - 10 * s},{y - 50 * s} L{x - 16 * s},{y - 30 * s} M{x + 10 * s},{y - 50 * s} L{x + 16 * s},{y - 30 * s}")
    elif arms == "wave":
        out += p(f"M{x - 10 * s},{y - 50 * s} L{x - 16 * s},{y - 30 * s} M{x + 10 * s},{y - 50 * s} L{x + 22 * s},{y - 74 * s}")
    elif arms == "phone":
        out += p(f"M{x - 10 * s},{y - 50 * s} L{x - 6 * s},{y - 40 * s} L{x + 4 * s},{y - 44 * s} M{x + 10 * s},{y - 50 * s} L{x + 6 * s},{y - 42 * s}")
        out += p(f"M{x + 1 * s},{y - 50 * s} h{8 * s} v{12 * s} h{-8 * s} z", fill="#333", w=1.4)
    elif arms == "lamp":
        out += p(f"M{x - 10 * s},{y - 50 * s} L{x - 16 * s},{y - 30 * s} M{x + 10 * s},{y - 50 * s} L{x + 20 * s},{y - 42 * s}")
        out += p(f"M{x + 17 * s},{y - 40 * s} q{4 * s},{-8 * s} {9 * s},0 q{-4 * s},{6 * s} {-9 * s},0", fill=SUN, w=1.6)
        out += p(f"M{x + 21.5 * s},{y - 46 * s} q{-3 * s},{-6 * s} {1 * s},{-10 * s} q{2 * s},{6 * s} {-1 * s},{10 * s}", fill="#ff9d3b", w=1.2)
    # head
    out += c(hx, hy, hr, fill="#fff4e5")
    if who == "bro":  # cap
        out += p(f"M{hx - hr},{hy - 2 * s} Q{hx},{hy - hr * 1.9} {hx + hr},{hy - 2 * s} Z", fill="#2a78d6", w=1.8)
        out += p(f"M{hx + hr * 0.6},{hy - 3 * s} L{hx + hr * 1.7},{hy - 1 * s}", w=2.2)
    if who == "amma":  # bun + bindi
        out += c(hx - hr * 0.95, hy - hr * 0.55, 5 * s, fill=INK, w=1)
        out += p(f"M{hx - hr},{hy - 1 * s} Q{hx},{hy - hr * 1.6} {hx + hr},{hy - 1 * s}", fill=INK, w=1)
        out += f'<circle cx="{hx:.1f}" cy="{hy - 6 * s:.1f}" r="{1.6 * s:.1f}" fill="#c0392b"/>'
    if who == "meera":  # ponytail
        out += p(f"M{hx - hr},{hy - 1 * s} Q{hx},{hy - hr * 1.6} {hx + hr},{hy - 1 * s}", fill="#3b2a1f", w=1)
        out += p(f"M{hx + hr * 0.8},{hy - hr * 0.6} q{9 * s},{4 * s} {6 * s},{16 * s}", w=3.2, stroke="#3b2a1f")
    if who == "dadaji":  # white hair, moustache, stick
        out += p(f"M{hx - hr},{hy - 2 * s} Q{hx - hr},{hy - hr * 1.2} {hx - 3 * s},{hy - hr}", w=2, stroke="#9aa0a6")
        out += p(f"M{hx - 4 * s},{hy + 3.5 * s} q{4 * s},{-2 * s} {8 * s},0", w=2)
        out += p(f"M{x + 16 * s},{y - 30 * s} L{x + 20 * s},{y}", w=2.6, stroke="#8a5a2b")
    if who == "chhotu":
        out += p(f"M{hx - 3 * s},{hy - hr} q{3 * s},{-6 * s} {6 * s},0", w=1.6)
    out += face(hx, hy, s * (1.05 if who == "chhotu" else 1), glasses=(who == "dadaji"))
    return out


def palm(x, y, s=1.0, fill=LEAF, eyes=True):
    """Palm, the guide: an open hand (the abhaya gesture) with a kind face. (x, y) = wrist bottom centre."""
    d = (f"M{x - 22 * s},{y} C{x - 26 * s},{y - 30 * s} {x - 36 * s},{y - 52 * s} {x - 30 * s},{y - 58 * s} "
         f"C{x - 24 * s},{y - 64 * s} {x - 18 * s},{y - 46 * s} {x - 16 * s},{y - 40 * s} "
         f"C{x - 18 * s},{y - 70 * s} {x - 20 * s},{y - 92 * s} {x - 12 * s},{y - 94 * s} "
         f"C{x - 4 * s},{y - 96 * s} {x - 6 * s},{y - 70 * s} {x - 4 * s},{y - 56 * s} "
         f"C{x - 4 * s},{y - 84 * s} {x - 4 * s},{y - 104 * s} {x + 4 * s},{y - 104 * s} "
         f"C{x + 12 * s},{y - 104 * s} {x + 8 * s},{y - 80 * s} {x + 8 * s},{y - 56 * s} "
         f"C{x + 10 * s},{y - 80 * s} {x + 14 * s},{y - 96 * s} {x + 21 * s},{y - 94 * s} "
         f"C{x + 29 * s},{y - 92 * s} {x + 22 * s},{y - 66 * s} {x + 20 * s},{y - 50 * s} "
         f"C{x + 24 * s},{y - 66 * s} {x + 30 * s},{y - 76 * s} {x + 35 * s},{y - 72 * s} "
         f"C{x + 41 * s},{y - 67 * s} {x + 30 * s},{y - 40 * s} {x + 26 * s},{y - 22 * s} "
         f"C{x + 24 * s},{y - 10 * s} {x + 22 * s},{y - 2 * s} {x + 20 * s},{y} Z")
    out = p(d, fill=fill)
    if eyes:
        out += dot(x - 6 * s, y - 34 * s, 2.2 * s) + dot(x + 8 * s, y - 34 * s, 2.2 * s)
        out += p(f"M{x - 6 * s},{y - 24 * s} Q{x + 1 * s},{y - 17 * s} {x + 8 * s},{y - 24 * s}", w=2)
    return out


def logo(size=40):
    """Small palm logo with a heart in the palm (for header and favicon)."""
    inner = palm(34, 112, 1.0, fill=LEAF, eyes=False)
    inner += p("M30,74 c-6,-8 -16,-2 -10,6 l10,10 l10,-10 c6,-8 -4,-14 -10,-6 z", fill=WARN, w=1.6)
    return (f'<svg class="logo" width="{size}" height="{size}" viewBox="-6 0 82 118" role="img" aria-label="Making Human Safe logo: an open palm with a heart">'
            f'{WOBBLE}<g filter="url(#wob)">{inner}</g></svg>')


def waves(x1, x2, y, n=None, color="#2a78d6", w=2.0, amp=8):
    n = n or max(2, int((x2 - x1) / 34))
    step = (x2 - x1) / n
    d = f"M{x1},{y}" + "".join(f" q{step / 2},{-amp} {step},0" for _ in range(n))
    return p(d, stroke=color, w=w)


# ---------------------------------------------------------------- the 12 launch doodles
def hero_wait():
    i = p("M0,250 L460,250 L460,330 L0,330 Z", fill=SEA, w=0)
    i += p("M0,250 C 80,238 160,262 240,246 C 320,232 400,256 460,244", fill="none", w=2.2, stroke="#2a78d6")
    i += waves(10, 200, 285) + waves(220, 440, 305)
    i += p("M150,252 C 190,244 250,250 320,247 C 360,262 380,300 400,330 L120,330 C 130,300 140,270 150,252 Z", fill=SAND, w=0)
    i += person(250, 252, "bro", 1.25, arms="down")
    i += palm(340, 190, 1.05)
    i += p("M500,80 L500,300 M500,80 L680,80 L680,300 M520,300 L520,120 L660,120 L660,300", w=2.4)
    i += p("M520,300 L660,300", w=2.4)
    i += person(585, 298, "amma", 1.25, arms="lamp")
    txt = t(335, 222, "wait!", 30, 700) + t(700, 140, "Someone is", 38, 700) + t(700, 186, "waiting for you.", 38, 700)
    txt += t(700, 230, "Know the place.", 24) + t(700, 262, "Then enjoy it.", 24)
    return svg(980, 330, "Bro is about to walk into a rough sea when Palm, the open hand, says wait. At home, Amma waits at the door with a lamp.", i, txt)


def cast_sheet():
    i = ""
    who = [("amma", "Amma", "waits at home"), ("bro", "Bro", "takes risks"), ("meera", "Meera", "travels solo"),
           ("dadaji", "Dadaji", "at home, careful steps"), ("chhotu", "Chhotu", "small, curious")]
    txt = ""
    for k, (w, name, line) in enumerate(who):
        x = 70 + k * 150
        i += person(x, 210, w, 1.35, arms="wave" if w in ("bro", "chhotu") else "down")
        txt += t(x, 248, name, 26, 700, "middle") + t(x, 274, line, 18, 400, "middle")
    i += palm(850, 214, 1.1)
    txt += t(850, 248, "Palm", 26, 700, "middle") + t(850, 274, "the guide: “wait”", 18, 400, "middle")
    return svg(940, 290, "The cast: Amma who waits at home, Bro who takes risks, Meera who travels solo, Dadaji the grandfather, Chhotu the child, and Palm the open-hand guide.", i, txt)


def rip_current():
    i = p("M0,0 L900,0 L900,250 L0,250 Z", fill=SEA, w=0) + p("M0,250 L900,250 L900,340 L0,340 Z", fill=SAND, w=0)
    i += p("M0,250 C150,240 300,258 450,248 C600,238 750,256 900,246", w=2.2, stroke="#2a78d6")
    for y in (70, 120, 170, 215):
        i += waves(20, 360, y) + waves(540, 880, y)
    i += p("M390,250 C380,180 360,110 410,40 M500,250 C510,180 530,110 480,40", w=2, stroke="#1b4f9c", extra='stroke-dasharray="6 6"')
    i += arrow(445, 230, 445, 70, color=WARN, w=3.4)
    i += person(445, 150, "bro", 0.8, arms="wave")
    i += arrow(470, 120, 620, 120, color="#17795a", w=3.4) + arrow(640, 128, 700, 230, color="#17795a", w=3.4)
    i += p("M120,300 l0,-50 M120,250 l30,10 l-30,10", w=2.4, fill=WARN)
    txt = t(330, 30, "rip current: calm-looking gap, pulls OUT", 22, 700)
    txt += t(632, 104, "1. swim SIDEWAYS", 24, 700, color="#17795a") + t(705, 200, "2. then back in", 22, 700, color="#17795a")
    txt += t(200, 296, "don't fight it, float and wave for help", 22) + t(110, 330, "red flag = no swimming", 18)
    return svg(900, 340, "Rip current escape: a calm-looking gap in the waves pulls a swimmer out to sea. Don't swim straight back; swim sideways, parallel to the beach, then back in. A red flag means no swimming.", i, txt)


def monsoon_sea():
    i = p("M0,0 L900,0 L900,300 L0,300 Z", fill="#e9eef5", w=0)
    for x in (120, 330, 560, 760):
        i += p(f"M{x - 70},70 c-20,0 -20,-34 6,-34 c4,-26 44,-30 54,-8 c18,-18 52,-6 46,16 c26,0 26,26 4,26 z", fill="#b8c2cf")
        i += p(f"M{x - 40},92 l-8,22 M{x - 6},92 l-8,22 M{x + 28},92 l-8,22", w=1.8, stroke="#5d7a99")
    i += p("M0,230 C80,150 140,140 200,200 C260,140 330,130 400,205 C470,140 540,135 600,200 C660,145 740,140 900,210 L900,300 L0,300 Z", fill="#a9c7ee")
    i += p("M60,300 L60,190 M60,190 l36,10 l-36,12", w=2.6, fill=WARN)
    i += person(820, 296, "amma", 1.0, arms="down") + person(860, 296, "chhotu", 1.0, arms="down")
    txt = t(110, 262, "June to September: big swells, rip currents", 24, 700)
    txt += t(110, 290, "most drownings happen in May and June", 20) + t(640, 140, "watch from the sand", 22, 700, color="#17795a")
    return svg(900, 300, "Monsoon sea: from June to September dark clouds bring big swells and rip currents. A red flag is up. Amma and Chhotu watch from the sand instead of swimming.", i, txt)


def waterfall_rise():
    i = p("M0,0 L900,0 L900,320 L0,320 Z", fill="#f2f7f2", w=0)
    i += p("M80,60 c-20,0 -20,-30 6,-30 c6,-22 46,-22 50,0 c22,-4 30,26 6,30 z", fill="#b8c2cf")
    i += p("M70,74 l-6,18 M100,74 l-6,18 M130,74 l-6,18", w=1.8, stroke="#5d7a99")
    i += p("M200,40 L330,40 L330,90 L200,90 Z", fill="#d9cbb3") + p("M240,90 L240,250 M262,90 L262,250 M284,90 L284,250", w=2.2, stroke="#2a78d6")
    i += p("M150,250 C300,240 500,262 900,248 L900,320 L150,320 Z", fill=SEA)
    i += p("M150,232 C300,222 500,244 900,230", w=2, stroke="#1b4f9c", extra='stroke-dasharray="7 6"')
    i += p("M500,250 C520,236 560,236 580,250 Z", fill="#c9b79c") + person(540, 240, "bro", 0.85, arms="phone")
    i += arrow(640, 300, 640, 226, color=WARN, w=3.4)
    txt = t(30, 128, "rain upstream", 20) + t(350, 70, "water can rise in minutes, even with no rain here", 22, 700)
    txt += t(655, 268, "rising", 22, 700, color=WARN) + t(560, 200, "no selfies on wet rocks", 22, 700)
    txt += t(160, 312, "get off rocks when water turns brown or louder", 18)
    return svg(900, 320, "Waterfall danger: rain far upstream can make the water rise within minutes even when it is sunny here. Bro takes a selfie on a wet rock as the water rises. Get off rocks when the water turns brown or gets louder.", i, txt)


def boat_jackets():
    i = p("M0,0 L900,0 L900,300 L0,300 Z", fill=SKY, w=0) + p("M0,200 L900,200 L900,300 L0,300 Z", fill=SEA, w=0)
    i += waves(0, 900, 205)
    i += p("M200,190 L700,190 L640,250 L260,250 Z", fill="#e6d3b3")
    for k, w in enumerate(["amma", "bro", "meera", "chhotu"]):
        x = 300 + k * 90
        i += person(x, 192, w, 0.95, arms="down")
        i += p(f"M{x - 12},{150 - (8 if w == 'chhotu' else 0)} h24 v{20 if w != 'chhotu' else 12} h-24 z", fill="#ff8c1a", w=1.8)
    i += p("M120,120 h70 v60 h-70 z", fill=PAPER) + p("M132,138 l6,6 l10,-12 M132,160 l6,6 l10,-12", w=2, stroke="#17795a")
    txt = t(330, 60, "count the life jackets before you step in", 26, 700)
    txt += t(250, 290, "one for each person, worn and buckled, not under the seat", 22)
    txt += t(110, 112, "checklist", 18)
    return svg(900, 300, "Boat safety: a family in a boat, each wearing a buckled orange life jacket. Count the life jackets before you board; one per person, worn, not kept under the seat.", i, txt)


def gas_leak():
    i = p("M40,40 L860,40 L860,300 L40,300 Z", fill="#fffaf2")
    i += p("M80,220 h180 v80 h-180 z", fill="#e9e3d6") + p("M100,150 h40 v70 h-40 z M100,150 q20,-14 40,0", fill="#e34948")
    i += p("M150,140 q10,-14 0,-28 q-10,-14 0,-28 M175,150 q10,-14 0,-28 q-10,-14 0,-28", w=1.8, stroke="#8aa04a")
    steps = [("1. don't touch switches", 330, 90), ("2. turn off regulator", 330, 135), ("3. open doors and windows", 330, 180),
             ("4. go outside", 330, 225), ("5. call 1906 (LPG emergency, India)", 330, 270)]
    i += p("M300,60 h400 v230 h-400 z", fill=PAPER, w=1.8)
    i += p("M720,90 h110 v150 h-110 z M775,90 v150 M720,165 h110", fill=SKY, w=2)
    i += person(780, 300, "amma", 0.9, arms="wave")
    txt = t(70, 90, "smell gas?", 30, 700)
    txt += "".join(t(x, y, s, 22, 700 if k == 4 else 400) for k, (s, x, y) in enumerate(steps))
    return svg(900, 320, "Gas leak at home: if you smell gas, don't touch any switches, turn off the cylinder regulator, open doors and windows, go outside, and call 1906, India's LPG emergency number.", i, txt)


def home_falls():
    i = p("M60,60 L840,60 L840,320 L60,320 Z", fill="#fffaf2") + p("M450,60 L450,320 M60,190 L450,190", w=2.4)
    i += p("M80,300 h120 v-30 h-120 z", fill="#cfe3fb") + p("M90,255 q30,-10 60,0", w=1.8, stroke="#2a78d6")
    ring = lambda x, y, r: f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="#e34948" stroke-width="3" stroke-dasharray="9 7"/>'
    i += ring(130, 286, 46) + p("M490,320 L490,270 L540,270 L540,230 L590,230 L590,190 L640,190 L640,150 L700,150", w=2.4)
    i += ring(600, 220, 70) + p("M150,180 h130 v-6 h-130 z", fill="#e6b8a2") + ring(215, 176, 44)
    i += person(760, 318, "dadaji", 1.0, arms="down")
    txt = t(80, 100, "3 places elders fall", 26, 700) + t(180, 250, "wet bathroom floor", 20) + t(270, 160, "loose rugs", 20)
    txt += t(520, 110, "stairs without a rail", 20) + t(470, 350, "fix: grab bars, anti-slip mats, night lights, a rail", 20, 700)
    return svg(900, 360, "Elderly falls at home happen in three places: a wet bathroom floor, loose rugs, and stairs without a rail. The fix: grab bars, anti-slip mats, night lights and a stair rail. Dadaji stands nearby with his walking stick.", i, txt)


def taxi_scam():
    i = p("M0,0 L900,0 L900,300 L0,300 Z", fill="#fffaf2", w=0) + p("M0,250 L900,250", w=2)
    i += p("M120,200 q10,-60 70,-60 h120 q50,0 70,60 h30 v40 h-320 v-40 z", fill=SUN) + c(170, 244, 20, fill="#555") + c(380, 244, 20, fill="#555")
    i += p("M230,140 h40 v-14 h-40 z", fill="#333", w=1.6) + person(520, 250, "meera", 1.1, arms="phone")
    i += p("M620,70 h220 v130 h-220 z", fill=PAPER) + p("M640,110 h180 M640,140 h180 M640,170 h120", w=1.6)
    txt = t(150, 100, "₹1,500!", 34, 700, color=WARN) + t(640, 100, "fair fare board", 22, 700)
    txt += t(650, 135, "airport to Calangute", 18) + t(650, 165, "check before you sit", 18, 700, color="#17795a")
    txt += t(120, 290, "know the fair fare first; use the prepaid counter or the official app", 22)
    return svg(900, 300, "Taxi scam: a driver shouts a price three times too high. Meera checks the fair fare on her phone and the official fare board before getting in, and uses the prepaid counter or the official app.", i, txt)


def report_helper():
    i = p("M330,30 h240 v280 h-240 z", fill=PAPER) + p("M350,60 h200 v200 h-200 z", fill="#eef5fe", w=1.6)
    i += p("M450,100 c-24,0 -36,32 0,72 c36,-40 24,-72 0,-72 z", fill=WARN, w=2) + c(450, 124, 9, fill=PAPER, w=1.8)
    i += p("M370,210 h160 M370,232 h120", w=1.6) + person(170, 300, "meera", 1.25, arms="phone")
    i += palm(720, 290, 0.95)
    txt = t(40, 60, "saw something?", 28, 700) + t(40, 96, "what, where, when", 22) + t(610, 120, "no names,", 22, 700)
    txt += t(610, 150, "no faces", 22, 700) + t(370, 290, "your report helps the next person", 18)
    return svg(900, 320, "Report helper: Meera reports what happened, where and when on her phone with a map pin. Palm reminds her: no names and no faces. Your report helps the next person.", i, txt)


def make_us_safe_steps():
    i = ""
    cols = [("#fff4e5", "1 · Who"), ("#e8f0fc", "2 · Where & when"), ("#e4f3ed", "3 · What you'll do"), ("#fdecec", "4 · Your brief")]
    txt = ""
    for k, (f, h) in enumerate(cols):
        x = 14 + k * 222
        i += p(f"M{x},30 h200 v220 h-200 z", fill=f)
        if k < 3:
            i += arrow(x + 204, 140, x + 218, 140)
        txt += t(x + 14, 62, h, 22, 700)
    i += person(55, 220, "dadaji", 0.85) + person(100, 220, "amma", 0.85) + person(145, 220, "bro", 0.85) + person(185, 220, "chhotu", 0.85)
    i += p("M320,100 c-24,0 -36,32 0,72 c36,-40 24,-72 0,-72 z", fill=WARN) + c(320, 124, 9, fill=PAPER, w=1.8)
    i += p("M270,190 h50 v40 h-50 z M270,202 h50", fill=PAPER, w=1.8)
    i += waves(470, 600, 210) + person(540, 200, "bro", 0.7, arms="wave") + p("M610,170 l20,-40 l20,40 z", fill=LEAF)
    i += p("M690,80 h100 v150 h-100 z", fill=PAPER) + "".join(p(f"M704,{y} l6,6 l10,-12 M728,{y} h50", w=1.8, stroke="#17795a") for y in (110, 145, 180))
    i += p("M820,140 q0,-24 20,-24 q20,0 20,24 v20 l8,10 h-56 l8,-10 z", fill=SUN)
    txt += t(28, 244, "grandpa, Amma, me, Chhotu", 16) + t(250, 244, "Gokarna, 20–23 Dec", 16)
    txt += t(470, 244, "swim, trek, night drive", 16) + t(690, 244, "risks, alerts, checklist", 16)
    return svg(900, 260, "MakeUsSafe in four steps: who is going, where and when, what you will do, and your personal safety brief with risks, live alerts and a checklist.", i, txt)


def co_pilot():
    i = p("M0,0 L900,0 L900,300 L0,300 Z", fill="#f3f4f6", w=0) + p("M0,250 L900,250", w=2)
    i += p("M120,250 v-60 q20,-70 120,-70 h220 q80,0 120,70 h60 v60 z", fill="#9cc3f5")
    i += p("M270,190 v-60 h170 q50,0 70,60 z", fill="#eef5fe", w=2) + c(220, 250, 26, fill="#555") + c(560, 250, 26, fill="#555")
    i += person(330, 210, "amma", 0.85, arms="down") + person(440, 210, "bro", 0.85, arms="phone")
    i += p("M640,120 h170 v70 h-170 z", fill=PAPER) + p("M660,140 h120 M660,160 h90", w=1.6)
    txt = t(150, 70, "driver: eyes on the road", 24, 700) + t(420, 100, "co-pilot: reports hazards", 24, 700, color="#17795a")
    txt += t(660, 210, "one tap warns everyone behind you", 18) + t(150, 290, "the driver never touches the phone", 22)
    return svg(900, 300, "Be the co-pilot: Amma drives with her eyes on the road while Bro, in the passenger seat, taps the phone to report a hazard. The driver never touches the phone.", i, txt)


ALL = [("hero-wait", hero_wait), ("cast", cast_sheet), ("rip-current", rip_current), ("monsoon-sea", monsoon_sea),
       ("waterfall", waterfall_rise), ("boat-jackets", boat_jackets), ("gas-leak", gas_leak), ("home-falls", home_falls),
       ("taxi-scam", taxi_scam), ("report", report_helper), ("make-us-safe", make_us_safe_steps), ("co-pilot", co_pilot)]
