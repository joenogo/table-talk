#!/usr/bin/env python3
"""
Generates site/index.html — a standalone page, no build step, no backend.

The page pulls live Premier League data straight from ESPN's public JSON API
in the browser (that API sends `access-control-allow-origin: *`, so no proxy
is needed) and recomputes everyone's score every minute while games are on.

Only reason this script exists: to inject the eight players' predictions from
the CSV without hand-transcribing 160 values. Re-run it if the picks change.

    python3 make.py
"""

import base64
import csv
import json
import pathlib

from _skins import SKINS

HERE = pathlib.Path(__file__).parent
CSV_PATH = HERE / "premier-league-predictions-2026-27.csv"
SITE = HERE / "site"
AUDIO = HERE / "audio"     # embedded so each page stays a single file
BADGE_DIR = HERE / "badges"
ART = HERE / "art"          # the Premier League lion, cropped out of the full lockup

# ESPN team id -> the name used in the predictions CSV. Ids are stable; names drift.
ESPN_IDS = {
    "359": "Arsenal",
    "362": "Aston Villa",
    "349": "Bournemouth",
    "337": "Brentford",
    "331": "Brighton",
    "363": "Chelsea",
    "388": "Coventry",
    "384": "Crystal Palace",
    "368": "Everton",
    "370": "Fulham",
    "306": "Hull City",
    "373": "Ipswich",
    "357": "Leeds",
    "364": "Liverpool",
    "382": "Manchester City",
    "360": "Manchester United",
    "361": "Newcastle",
    "393": "Nottingham Forest",
    "366": "Sunderland",
    "367": "Tottenham",
}

# Full club names, used wherever there is room for them.
FULL = {
    "Arsenal": "Arsenal", "Aston Villa": "Aston Villa", "Bournemouth": "AFC Bournemouth",
    "Brentford": "Brentford", "Brighton": "Brighton & Hove Albion", "Chelsea": "Chelsea",
    "Coventry": "Coventry City", "Crystal Palace": "Crystal Palace", "Everton": "Everton",
    "Fulham": "Fulham", "Hull City": "Hull City", "Ipswich": "Ipswich Town",
    "Leeds": "Leeds United", "Liverpool": "Liverpool", "Manchester City": "Manchester City",
    "Manchester United": "Manchester United", "Newcastle": "Newcastle United",
    "Nottingham Forest": "Nottingham Forest", "Sunderland": "Sunderland",
    "Tottenham": "Tottenham Hotspur",
}

# Compact forms for narrow columns — shortened, never nicknamed.
SHORT = {
    "Arsenal": "Arsenal", "Aston Villa": "Aston Villa", "Bournemouth": "Bournemouth",
    "Brentford": "Brentford", "Brighton": "Brighton", "Chelsea": "Chelsea",
    "Coventry": "Coventry", "Crystal Palace": "Crystal Palace", "Everton": "Everton",
    "Fulham": "Fulham", "Hull City": "Hull City", "Ipswich": "Ipswich",
    "Leeds": "Leeds", "Liverpool": "Liverpool", "Manchester City": "Man City",
    "Manchester United": "Man Utd", "Newcastle": "Newcastle",
    "Nottingham Forest": "Nott'm Forest", "Sunderland": "Sunderland",
    "Tottenham": "Tottenham",
}

# The three who have not handed a table in yet. They are in the pot; they just
# cannot be scored until their column appears in the CSV.
PENDING = []

BUY_IN = 25
PRIZES = [125, 90, 60]          # 1st, 2nd, 3rd


def audio_uri(name, mime):
    p = AUDIO / name
    if not p.exists():
        raise SystemExit(f"missing audio/{name} — it is embedded into the page")
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode("ascii")


def crowd_data_uri():
    return audio_uri("crowd.m4a", "audio/mp4")


def favicon_uri():
    """The lion on an opaque paper square so it reads on a dark browser tab.
    Wrapping it in an SVG lets us composite without decoding the PNG."""
    png = ART / "crest96.png"
    if not png.exists():
        raise SystemExit(f"missing art/{png.name} — the favicon is built from it")
    b64 = base64.b64encode(png.read_bytes()).decode("ascii")
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
           '<rect width="64" height="64" fill="#f3f1ea"/>'
           f'<image x="5" y="5" width="54" height="54" href="data:image/png;base64,{b64}"/>'
           '</svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode("ascii")


def badge_uris():
    """club name -> data URI. Empty dict if the badge folder is absent."""
    if not BADGE_DIR.exists():
        return {}
    slug_to_club = {
        "arsenal": "Arsenal", "villa": "Aston Villa", "bournemouth": "Bournemouth",
        "brentford": "Brentford", "brighton": "Brighton", "chelsea": "Chelsea",
        "coventry": "Coventry", "palace": "Crystal Palace", "everton": "Everton",
        "fulham": "Fulham", "hull": "Hull City", "ipswich": "Ipswich",
        "leeds": "Leeds", "liverpool": "Liverpool", "mancity": "Manchester City",
        "manutd": "Manchester United", "newcastle": "Newcastle",
        "forest": "Nottingham Forest", "sunderland": "Sunderland", "spurs": "Tottenham",
    }
    out = {}
    for p in sorted(BADGE_DIR.glob("*.png")):
        club = slug_to_club.get(p.stem)
        if club:
            out[club] = "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode("ascii")
    missing = set(ESPN_IDS.values()) - set(out)
    if out and missing:
        raise SystemExit(f"badges/ is missing: {sorted(missing)}")
    return out


def money_config(submitted):
    players = len(submitted) + len(PENDING)
    pot = BUY_IN * players
    if sum(PRIZES) != pot:
        raise SystemExit(
            f"prizes {PRIZES} total ${sum(PRIZES)} but the pot is ${pot} "
            f"({players} players x ${BUY_IN})"
        )
    return {"buyIn": BUY_IN, "players": players, "pot": pot, "prizes": PRIZES}


def load_predictions():
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    players = [c for c in rows[0] if c != "Position"]
    preds = {p: {} for p in players}
    for row in rows:
        pos = int(row["Position"])
        for p in players:
            preds[p][row[p].strip()] = pos

    known = set(ESPN_IDS.values())
    for p in players:
        picks = set(preds[p])
        if picks != known:
            raise SystemExit(
                f"{p}: predictions don't match the league.\n"
                f"  unknown: {sorted(picks - known)}\n"
                f"  missing: {sorted(known - picks)}"
            )
        if len(preds[p]) != 20:
            raise SystemExit(f"{p} has {len(preds[p])} teams, expected 20")
    return players, preds


def build():
    players, preds = load_predictions()
    m = money_config(players)
    badges = badge_uris()
    crowd = crowd_data_uri()
    SITE.mkdir(exist_ok=True)

    common = {
        "__PREDICTIONS__": json.dumps(preds, separators=(",", ":"), sort_keys=True),
        "__TEAMS__": json.dumps(ESPN_IDS, separators=(",", ":"), sort_keys=True),
        "__SHORT__": json.dumps(SHORT, separators=(",", ":"), sort_keys=True),
        "__FULL__": json.dumps(FULL, separators=(",", ":"), sort_keys=True),
        "__PENDING__": json.dumps(PENDING, separators=(",", ":")),
        "__MONEY__": json.dumps(m, separators=(",", ":")),
        "__CROWD__": crowd,
        "__FAVICON__": favicon_uri(),
    }

    print(f"  submitted ({len(players)}): {', '.join(players)}")
    print(f"  pending   ({len(PENDING)}): {', '.join(PENDING)}")
    print(f"  pot ${m['pot']} = ${m['buyIn']} x {m['players']}  ->  {m['prizes']}")

    for skin, cfg in SKINS.items():
        html = TEMPLATE
        for k, v in common.items():
            html = html.replace(k, v)
        html = (html
                .replace("__SKIN_CSS__", cfg["css"])
                .replace("__FONTS__", cfg["fonts"])
                .replace("__TITLE__", cfg["title"])
                .replace("__MAST__", cfg["mast"])
                .replace("__BADGES__",
                         json.dumps(badges, separators=(",", ":"), sort_keys=True)
                         if cfg["badges"] else "{}"))
        left = [t for t in ("__PREDICTIONS__", "__SKIN_CSS__", "__BADGES__", "__FULL__",
                            "__CROWD__", "__FAVICON__", "__MAST__", "__TITLE__", "__FONTS__") if t in html]
        if left:
            raise SystemExit(f"{skin}: unsubstituted {left}")
        out = SITE / cfg["out"]
        out.write_text(html, encoding="utf-8")
        fallback = ART / "crest180.png"
        if fallback.exists():
            (SITE / "favicon.png").write_bytes(fallback.read_bytes())
        print(f"  {skin:<10} -> site/{cfg['out']:<16} {len(html):>9,} bytes"
              f"  badges={'yes' if cfg['badges'] else 'no'}")
TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<meta name="description" content="Eleven predicted Premier League tables, scored live against the real one. Lowest total wins.">
<link rel="icon" type="image/svg+xml" href="__FAVICON__">
<link rel="icon" type="image/png" href="favicon.png">
<link rel="apple-touch-icon" href="favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
__FONTS__
<style>
/* ===================== SHARED STRUCTURE ===================== */
* { box-sizing: border-box; }
html { background: var(--bg); }

body {
  margin: 0; background: var(--bg); color: var(--ink);
  font-family: var(--body); font-size: 15px; line-height: 1.5;
  font-variant-numeric: tabular-nums; -webkit-font-smoothing: antialiased;
}
body::before {
  content: ""; position: fixed; inset: 0; z-index: 9; pointer-events: none;
  background: repeating-linear-gradient(180deg, var(--scan) 0 1px, transparent 1px 3px);
}
.page { max-width: 1120px; margin: 0 auto; padding: 0 16px 72px; position: relative; z-index: 1; }

/* ---------- goal celebration: a printed banner, not floating bits ---------- */
.cel {
  position: fixed; inset: 0; z-index: 40; pointer-events: none;
  display: grid; place-items: center;
  animation: celout .45s ease-in 7.5s forwards;
}
@keyframes celout { to { opacity: 0; } }

.cel-scrim {
  position: absolute; inset: 0; background: var(--bg); opacity: 0;
  pointer-events: auto; cursor: pointer;
  animation: scrimin .22s ease-out forwards;
}
@keyframes scrimin { to { opacity: .74; } }

.cel-band {
  position: relative; overflow: hidden;
  pointer-events: auto;               /* clicks on the banner itself must not close it */
  width: min(1100px, 94vw); height: clamp(170px, 30vh, 260px);
  background: var(--panel); color: var(--ink);
  border-top: 6px solid var(--ink); border-bottom: 6px solid var(--ink);
  box-shadow: 0 18px 50px rgba(0,0,0,.30);
  clip-path: inset(0 100% 0 0);
  animation: wipe .34s cubic-bezier(.2,.8,.2,1) .06s forwards;
}
@keyframes wipe { to { clip-path: inset(0 0 0 0); } }

.cel-text { position: absolute; left: 4.5%; top: 50%; transform: translateY(-50%); }
.cel-word {
  font-family: var(--disp); font-size: clamp(44px, 8.4vw, 118px);
  line-height: .84; letter-spacing: -.02em; text-transform: uppercase;
  color: var(--red); opacity: 0; transform: scale(1.35);
  animation: stamp .3s cubic-bezier(.2,1.6,.4,1) .46s forwards;
}
.cel-word span { color: var(--ylw); }
@keyframes stamp { to { opacity: 1; transform: none; } }
.cel-line {
  margin-top: 6px; font-family: var(--mono); font-size: clamp(11px, 1.35vw, 17px);
  letter-spacing: .16em; text-transform: uppercase; color: var(--dim);
  opacity: 0; transform: translateY(8px);
  animation: linein .28s ease-out .72s forwards;
}
@keyframes linein { to { opacity: 1; transform: none; } }

.cel-goal {
  position: absolute; right: 3.5%; bottom: 4%; width: 31%; color: var(--ink);
  opacity: 0; animation: netin .3s ease-out .12s forwards, netshake .3s ease-out .62s;
}
.cel-goal svg { display: block; width: 100%; height: auto; }
@keyframes netin { to { opacity: .55; } }
@keyframes netshake {
  0%, 100% { transform: none; }
  35% { transform: translate(4px, 2px) scaleX(1.015); }
  70% { transform: translate(-2px, -1px); }
}

.cel-ball {
  position: absolute; width: clamp(26px, 3.4vw, 44px);
  filter: drop-shadow(0 5px 8px rgba(0,0,0,.25));
  animation: ballcross .95s cubic-bezier(.32,.06,.6,1) forwards;
}
.cel-ball svg { display: block; width: 100%; height: auto; }
@keyframes ballcross {
  0%   { left: -8%; top: 62%; transform: rotate(0deg)   scale(.78); opacity: 0; }
  14%  { opacity: 1; }
  58%  { left: 66%; top: 24%; transform: rotate(500deg) scale(1); }
  66%  { left: 73%; top: 30%; transform: rotate(590deg) scale(1.12, .88); }
  100% { left: 78%; top: 56%; transform: rotate(760deg) scale(1); opacity: 1; }
}

@media (prefers-reduced-motion: reduce) { .cel { display: none; } }


/* ---------- header strip ---------- */
.strip { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 10px 0 9px; font-size: 12px; letter-spacing: .06em; }
.pageno { background: var(--mag); color: var(--chipink); font-weight: 700; padding: 3px 9px; font-family: var(--disp); font-size: 11px; }
.strip .svc { color: var(--cyn); font-weight: 700; letter-spacing: .18em; font-family: var(--disp); }
.strip .spacer { flex: 1 1 auto; }
.strip .clock { color: var(--ink); font-size: 12px; font-family: var(--mono); }
.strip .clock .d { color: var(--dim); }

.tbtn { background: transparent; border: 1px solid var(--line2); color: var(--dim); font: inherit; font-family: var(--mono); font-size: 10px; letter-spacing: .1em; padding: 4px 9px; cursor: pointer; }
.tbtn:hover { color: var(--ink); border-color: var(--ink); }
.tbtn[aria-pressed="true"] { border-color: var(--ylw); color: var(--ylw); }
.tbtn:focus-visible { outline: 2px solid var(--cyn); outline-offset: 1px; }
.seg { display: inline-flex; border: 1px solid var(--line2); }
.seg button { background: transparent; border: 0; color: var(--dim); font: inherit; font-family: var(--mono); font-size: 10px; letter-spacing: .08em; padding: 4px 8px; cursor: pointer; }
.seg button + button { border-left: 1px solid var(--line2); }
.seg button[aria-pressed="true"] { background: var(--cyn); color: var(--chipink); font-weight: 700; }
.seg button:focus-visible { outline: 2px solid var(--cyn); outline-offset: -2px; }

.rainbow { display: flex; height: 7px; }
.rainbow i { flex: 1; }
.rainbow i:nth-child(1) { background: var(--red); }
.rainbow i:nth-child(2) { background: var(--ylw); }
.rainbow i:nth-child(3) { background: var(--grn); }
.rainbow i:nth-child(4) { background: var(--cyn); }
.rainbow i:nth-child(5) { background: var(--blu); }
.rainbow i:nth-child(6) { background: var(--mag); }
.rainbow i:nth-child(7) { background: var(--ink); }

/* ---------- masthead ---------- */
.mast { padding: 28px 0 4px; }
.mast-grid { display: grid; grid-template-columns: 1fr; gap: 18px; align-items: start; }
@media (min-width: 860px) { .mast-grid { grid-template-columns: 1fr 296px; } }
.factsbox { border: 1px solid var(--line); background: var(--panel); padding: 13px 15px; box-shadow: var(--shadow); }
.factshd { font-family: var(--disp); font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: var(--dim); margin-bottom: 9px; }
.factslist { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 9px; }
.factslist li { font-size: 13px; line-height: 1.45; padding-left: 13px; position: relative; }
.factslist li::before { content: "\2014"; position: absolute; left: 0; top: 0; color: var(--red); }
.factslist li b { color: var(--ink); font-weight: 700; }
.mast h1 { margin: 0; font-family: var(--disp); font-weight: var(--h1w); font-size: clamp(40px, 10.5vw, 88px); line-height: .86; letter-spacing: var(--h1ls); color: var(--h1); text-shadow: var(--h1glow); text-transform: var(--h1tt); }
.mast h1 a { color: inherit; text-decoration: none; display: inline-block; }
.mast h1 a:focus-visible { outline: 3px solid var(--cyn); outline-offset: 4px; }

/* On hover the two words slide apart and each picks up an off-register colour
   ghost — a printing plate slipping, which is the right kind of trick for a
   matchday programme. */
.mast h1 a span, .mast h1 a em {
  display: block;
  transition: transform .32s cubic-bezier(.2,.85,.25,1), color .32s ease, text-shadow .32s ease;
}
.mast h1 a:hover span, .mast h1 a:focus-visible span, .mast h1 a.slip span {
  color: var(--blu); transform: translateX(-8px);
  text-shadow: 7px 0 0 color-mix(in srgb, var(--red) 60%, transparent);
}
.mast h1 a:hover em, .mast h1 a:focus-visible em, .mast h1 a.slip em {
  color: var(--red); transform: translateX(8px);
  text-shadow: -7px 0 0 color-mix(in srgb, var(--blu) 60%, transparent);
}
@media (prefers-reduced-motion: reduce) {
  .mast h1 a span, .mast h1 a em { transition: color .32s ease; }
  .mast h1 a:hover span, .mast h1 a:focus-visible span,
  .mast h1 a:hover em, .mast h1 a:focus-visible em { transform: none; text-shadow: none; }
}
.mast h1 em { font-style: normal; color: var(--h1b); display: block; }
.mast .tag {
  margin: 18px 0 0; font-size: 16px; color: var(--ink); max-width: 66ch;
  padding-bottom: 18px; border-bottom: 3px solid var(--ink);
}
.mast .tag b { color: var(--red); font-weight: 700; }

/* ---------- section headers ---------- */
h2 { font-family: var(--disp); font-weight: 700; font-size: 13px; letter-spacing: .1em; margin: 0; color: var(--chipink); background: var(--cyn); display: inline-block; padding: 4px 11px; text-transform: uppercase; }
h2.y { background: var(--ylw); } h2.g { background: var(--grn); }
h2.m { background: var(--mag); } h2.o { background: var(--org); } h2.v { background: var(--vio); }
.sec { margin-top: 40px; }
.sechead { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 13px; }
.sechead .hint { font-size: 12px; color: var(--dim); letter-spacing: .04em; }

/* ---------- pot ---------- */
.pot { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1px; background: var(--line); border: 1px solid var(--line); }
.potcell { background: var(--panel); padding: 12px 14px; }
.potcell .k { font-size: 10px; letter-spacing: .12em; color: var(--dim); font-family: var(--mono); }
.potcell .v { font-family: var(--disp); font-weight: 800; font-size: 24px; letter-spacing: -.03em; margin-top: 3px; }
.potcell.p1 .v { color: var(--ylw); } .potcell.p2 .v { color: var(--cyn); } .potcell.p3 .v { color: var(--org); }
.potnote { font-size: 13px; color: var(--dim); margin-top: 10px; }
.potnote b { color: var(--ink); font-weight: 600; }

/* ---------- ticker ---------- */
.ticker { border: 1px solid var(--line); background: var(--panel); box-shadow: var(--shadow); }
.ticker .thead { display: flex; align-items: center; gap: 10px; padding: 8px 13px; border-bottom: 1px solid var(--line); font-size: 11px; letter-spacing: .14em; color: var(--dim); font-family: var(--mono); }
.blink { color: var(--red); font-weight: 700; animation: bl 1.1s steps(1) infinite; }
@keyframes bl { 50% { opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .blink { animation: none; } }

.match { display: grid; grid-template-columns: 1fr 84px 1fr 48px; gap: 10px; align-items: center; max-width: 680px; margin: 0 auto; padding: 9px 13px; border-bottom: 1px solid var(--line); font-size: 14px; }
.match:last-child { border-bottom: none; }
.match .h { text-align: right; } .match .a { text-align: left; }
.match .bd { display: inline-flex; align-items: center; gap: 7px; }
.match .h .bd { flex-direction: row-reverse; }
.match img { width: 20px; height: 20px; object-fit: contain; flex: none; }
.match .sc { text-align: center; font-weight: 700; color: var(--ylw); font-family: var(--disp); font-size: 15px; letter-spacing: -.03em; }
.match.pre .sc { display: flex; flex-direction: column; align-items: center; gap: 1px; }
.match.pre .sc .scdate { font-family: var(--mono); font-size: 10px; letter-spacing: .06em; color: var(--dim); font-weight: 600; }
.match.pre .sc .sctime { font-family: var(--disp); font-size: 13px; font-weight: 700; color: var(--dim); letter-spacing: -.01em; }
.match .cl { text-align: right; font-size: 11px; color: var(--dim); font-family: var(--mono); }
.match.pre .sc { color: var(--dim); } .match.post .sc { color: var(--ink); }
.match.goal { background: color-mix(in srgb, var(--ylw) 12%, var(--panel)); }
.match.fresh .sc { animation: goalflash .5s steps(1) 20; border-radius: 2px; }
@keyframes goalflash { 50% { background: var(--ylw); color: var(--chipink); } }
.match.fresh .gl { color: var(--ylw); font-weight: 700; font-size: 10px; letter-spacing: .1em; animation: bl 1s steps(1) infinite; }
@media (prefers-reduced-motion: reduce) { .match.fresh .sc { animation: none; background: var(--ylw); color: var(--chipink); } .match.fresh .gl { animation: none; } }

/* ---------- goal report ---------- */
.goalcard { border: 1px solid var(--ylw); background: var(--panel); margin-top: 14px; box-shadow: var(--shadow); }
.goalcard .gh { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; background: var(--ylw); color: var(--chipink); padding: 6px 13px; font-family: var(--disp); font-weight: 700; font-size: 12px; letter-spacing: .08em; }
.goalcard .gb { padding: 11px 13px; display: flex; flex-direction: column; gap: 8px; font-size: 13px; }
.goalcard .grow { display: flex; flex-wrap: wrap; gap: 4px 14px; align-items: baseline; }
.goalcard .lab { font-size: 10px; letter-spacing: .12em; color: var(--dim); min-width: 92px; font-family: var(--mono); }
.goalcard .up { color: var(--grn); font-weight: 600; }
.goalcard .dn { color: var(--red); font-weight: 600; }
.goalcard .neu { color: var(--dim); }
.goalcard .crown { color: var(--ylw); font-weight: 700; }
.gclose { background: transparent; border: 1px solid currentColor; color: inherit; font: inherit; font-size: 10px; padding: 2px 7px; cursor: pointer; margin-left: auto; }

/* ---------- leaderboard ---------- */
.board { border: 1px solid var(--line); box-shadow: var(--shadow); }
.brow { display: grid; grid-template-columns: 1fr auto; border-bottom: 1px solid var(--line); background: var(--panel); }
.brow:nth-child(even) { background: var(--band); }
.brow:last-child { border-bottom: none; }
.brow.open { background: var(--hover); }
.flash { animation: rowflash 1.6s ease-out 2; }
@keyframes rowflash { 0%, 100% { background: var(--panel); } 40% { background: color-mix(in srgb, var(--ylw) 26%, var(--panel)); } }
@media (prefers-reduced-motion: reduce) { .flash { animation: none; outline: 2px solid var(--ylw); outline-offset: -2px; } }

.brmain { display: grid; grid-template-columns: 34px 1fr 156px 74px 92px; align-items: center; gap: 13px; background: transparent; color: inherit; border: 0; padding: 12px 6px 12px 13px; font: inherit; font-family: var(--body); cursor: pointer; text-align: left; }
.brmain:hover { background: var(--hover); }
.brmain:focus-visible { outline: 2px solid var(--cyn); outline-offset: -2px; }
.brow .pos { color: var(--dim); font-size: 13px; font-family: var(--mono); }
.brow.lead .pos { color: var(--ylw); }
.brow .nm { font-family: var(--disp); font-weight: 700; font-size: 18px; letter-spacing: -.02em; color: var(--ink); }
.brow.lead .nm { color: var(--ylw); }
.brow .bar { white-space: nowrap; overflow: hidden; display: block; }
.brow .bar b { font-family: var(--mono); font-size: 12px; letter-spacing: -1px; font-weight: 400; color: var(--dim); }
.brow .bar i { display: none; height: 8px; background: var(--line2); }
.brow .bar i em { display: block; height: 100%; background: currentColor; }
.brow .tot { text-align: right; font-family: var(--disp); font-weight: 700; font-size: 21px; letter-spacing: -.04em; }
.brow.lead .tot { color: var(--ylw); }
.brow .meta { text-align: right; font-size: 11px; color: var(--dim); white-space: nowrap; font-family: var(--mono); }
.brow .cash { display: block; font-weight: 700; font-size: 12px; }
.brow.m1 .cash { color: var(--ylw); } .brow.m2 .cash { color: var(--cyn); } .brow.m3 .cash { color: var(--org); }
.brow.noentry { opacity: .62; }
.brow.noentry .nm { color: var(--dim); }

.brcopy { background: transparent; border: 0; border-left: 1px solid var(--line); color: var(--dim); font: inherit; font-family: var(--mono); font-size: 10px; letter-spacing: .1em; padding: 0 12px; cursor: pointer; align-self: stretch; }
.brcopy:hover { color: var(--cyn); background: var(--hover); }
.brcopy:focus-visible { outline: 2px solid var(--cyn); outline-offset: -2px; }
.brcopy.done { color: var(--grn); }

.card { background: var(--band); border-bottom: 1px solid var(--line); padding: 15px 13px 13px; }
.card[hidden] { display: none; }
.card .kpis { display: flex; flex-wrap: wrap; gap: 7px 26px; font-size: 12px; color: var(--dim); letter-spacing: .03em; padding-bottom: 11px; margin-bottom: 12px; border-bottom: 1px solid var(--line); font-family: var(--mono); }
.card .kpis b { color: var(--ink); font-weight: 700; }

/* picks read DOWN each column: 1-5, 6-10, 11-15, 16-20 */
.pickcols { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px 26px; }
@media (max-width: 1000px) { .pickcols { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 560px)  { .pickcols { grid-template-columns: 1fr; } }
.pkhead { display: grid; grid-template-columns: 26px 1fr 34px 30px; gap: 8px; padding: 0 0 4px; margin-bottom: 3px; border-bottom: 1px solid var(--line2); font-family: var(--mono); font-size: 9px; letter-spacing: .1em; color: var(--dim); }
.pkhead span:nth-child(3), .pkhead span:nth-child(4) { text-align: right; }
.pk { display: grid; grid-template-columns: 26px 1fr 34px 30px; gap: 8px; align-items: baseline; font-size: 13px; padding: 4px 0; }
.pk .n { color: var(--dim); font-size: 12px; font-family: var(--mono); }
.pk .t { color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; gap: 6px; }
.pk .t img { width: 16px; height: 16px; object-fit: contain; flex: none; }
.pk .m { font-size: 11px; color: var(--dim); text-align: right; font-family: var(--mono); }
.pk .g { text-align: right; font-weight: 700; font-family: var(--mono); }

.g0 { color: var(--grn); } .g1 { color: var(--cyn); } .g2 { color: var(--ink); }
.g3 { color: var(--ylw); } .g4 { color: var(--red); }

/* ---------- legend ---------- */
.legend { display: flex; flex-wrap: wrap; gap: 6px 18px; margin-top: 11px; font-size: 11px; color: var(--dim); letter-spacing: .04em; font-family: var(--mono); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.legend i { width: 11px; height: 11px; display: inline-block; }

/* ---------- chart ---------- */
.chartwrap { border: 1px solid var(--line); background: var(--panel); padding: 13px 13px 9px; position: relative; box-shadow: var(--shadow); }
.chartwrap svg { display: block; width: 100%; height: auto; touch-action: pan-y; }
.racelegend { display: flex; flex-wrap: wrap; gap: 7px 20px; padding: 11px 2px 2px; font-size: 12px; letter-spacing: .03em; border-top: 1px solid var(--line); margin-top: 9px; font-family: var(--mono); }
.racelegend span { display: inline-flex; align-items: center; gap: 6px; }
.racelegend i { width: 10px; height: 10px; display: inline-block; }
.racelegend b { color: var(--ink); font-weight: 700; }
.tip { position: absolute; pointer-events: none; z-index: 5; background: var(--panel); border: 1px solid var(--line2); padding: 8px 10px; font-size: 12px; min-width: 160px; box-shadow: 0 6px 22px rgba(0,0,0,.32); display: none; font-family: var(--mono); }
.tip .td { font-size: 10px; letter-spacing: .1em; color: var(--dim); margin-bottom: 6px; }
.tip .tr { display: grid; grid-template-columns: 10px 1fr auto; gap: 7px; align-items: center; padding: 1px 0; }
.tip .tr i { width: 8px; height: 8px; }
.tip .tr b { font-weight: 700; }
.tip .tr.hi { background: var(--hover); margin: 0 -4px; padding: 1px 4px; }
.pending { padding: 24px 13px; color: var(--dim); font-size: 13px; text-align: center; border: 1px solid var(--line); background: var(--panel); }

/* ---------- odds ---------- */
.odds { border: 1px solid var(--line); background: var(--panel); box-shadow: var(--shadow); }
.orow { display: grid; grid-template-columns: 1fr 160px 62px; gap: 13px; align-items: center; padding: 9px 13px; border-bottom: 1px solid var(--line); font-size: 14px; }
.orow:last-child { border-bottom: none; }
.orow .on { font-family: var(--disp); font-weight: 700; font-size: 15px; }
.orow .track { display: block; height: 10px; background: var(--band); border: 1px solid var(--line); }
.orow .fill { display: block; height: 100%; }
.orow .pc { text-align: right; font-family: var(--disp); font-weight: 700; }

/* ---------- tables ---------- */
.scroll { overflow-x: auto; border: 1px solid var(--line); background: var(--panel); box-shadow: var(--shadow); }
table { border-collapse: collapse; width: 100%; font-size: 14px; color: var(--ink); font-family: var(--body); }
th, td { padding: 6px 10px; text-align: right; white-space: nowrap; }
thead th { font-size: 10px; letter-spacing: .1em; color: var(--dim); font-weight: 600; border-bottom: 1px solid var(--line2); background: var(--panel); position: sticky; top: 0; font-family: var(--mono); }
tbody tr:nth-child(even) { background: var(--band); }
.lg th:nth-child(3), .lg td:nth-child(3) { text-align: left; width: 100%; }
.lg td.bdg { width: 30px; text-align: center; padding: 3px 4px; }
.lg td.bdg img { width: 22px; height: 22px; object-fit: contain; vertical-align: middle; }
.gr th:first-child, .gr td:first-child { text-align: left; width: 100%; color: var(--ink); }
.gr td.club .cw, .dm td.club .cw { display: inline-flex; align-items: center; gap: 7px; vertical-align: middle; }
.gr td.club img, .dm td.club img { width: 18px; height: 18px; object-fit: contain; flex: none; }
.dm th:first-child, .dm td:first-child { text-align: left; width: 100%; color: var(--ink); }
td.rk { color: var(--dim); font-size: 12px; font-family: var(--mono); }
td.cl { color: var(--ink); }
td.pt { color: var(--ylw); font-weight: 700; font-family: var(--disp); }
tr.ucl td.rk { color: var(--grn); font-weight: 600; }
tr.rel td.rk { color: var(--red); font-weight: 600; }
tr.playing td.cl::after { content: " \25CF"; color: var(--red); font-size: 9px; vertical-align: middle; }

/* ---------- head to head ---------- */
.h2hpick { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 13px; font-size: 13px; color: var(--dim); }
.h2hpick select { background: var(--panel); color: var(--cyn); border: 1px solid var(--line2); font: inherit; font-family: var(--mono); font-size: 13px; padding: 5px 9px; }
.h2hpick select:focus-visible { outline: 2px solid var(--cyn); }
.h2hcard { border: 1px solid var(--line); background: var(--panel); box-shadow: var(--shadow); }
.h2hscore { display: grid; grid-template-columns: 1fr auto 1fr; gap: 14px; align-items: center; padding: 15px 14px; border-bottom: 1px solid var(--line2); }
.h2hscore .side { display: flex; flex-direction: column; gap: 3px; }
.h2hscore .side.r { text-align: right; align-items: flex-end; }
.h2hscore .who { font-family: var(--disp); font-weight: 700; font-size: 16px; letter-spacing: -.02em; }
.h2hscore .num { font-family: var(--disp); font-weight: 800; font-size: 32px; letter-spacing: -.04em; line-height: 1; }
.h2hscore .sub { font-size: 11px; color: var(--dim); font-family: var(--mono); }
.h2hscore .mid { text-align: center; font-size: 10px; letter-spacing: .12em; color: var(--dim); font-family: var(--mono); }
.h2hscore .mid b { display: block; font-family: var(--disp); font-size: 15px; margin-top: 3px; }
.h2hscore .win { color: var(--grn); }
.h2hbar { display: flex; height: 9px; }
.h2hbar i { display: block; }
.h2hcount { display: flex; flex-wrap: wrap; gap: 4px 22px; justify-content: center; padding: 9px 13px; border-bottom: 1px solid var(--line); font-size: 11px; letter-spacing: .08em; color: var(--dim); font-family: var(--mono); }
.h2hcount b { font-family: var(--disp); font-weight: 700; font-size: 13px; color: var(--ink); }
.h2hrow { display: grid; grid-template-columns: 58px 1fr 44px 1fr 58px; gap: 9px; align-items: center; padding: 7px 13px; border-bottom: 1px solid var(--line); font-size: 13px; }
.h2hrow:last-child { border-bottom: none; }
.h2hrow.hd { color: var(--dim); font-size: 10px; letter-spacing: .1em; background: var(--band); font-family: var(--mono); }
.h2hrow .club { color: var(--ink); text-align: center; display: flex; align-items: center; justify-content: center; gap: 7px; }
.h2hrow .club img { width: 17px; height: 17px; object-fit: contain; }
.h2hrow .v { text-align: center; font-weight: 700; font-family: var(--mono); }
.h2hrow .who { font-size: 10px; letter-spacing: .06em; font-family: var(--mono); }
.h2hrow .lft { text-align: right; } .h2hrow .rgt { text-align: left; }

/* ---------- status ---------- */
.status { margin-top: 34px; padding-top: 13px; border-top: 1px solid var(--line); display: flex; flex-wrap: wrap; gap: 6px 20px; justify-content: space-between; font-size: 11px; color: var(--dim); letter-spacing: .04em; font-family: var(--mono); }
.status .err { color: var(--red); }
.note { margin-top: 16px; padding: 12px 14px; border-left: 3px solid var(--ylw); background: var(--panel); font-size: 13px; color: var(--dim); }
.note b { color: var(--ylw); font-weight: 700; }
.soundhint {
  position: fixed; left: 50%; bottom: 22px; transform: translateX(-50%);
  display: flex; align-items: center; gap: 9px;
  background: var(--ink); color: var(--bg);
  font-family: var(--mono); font-size: 12px; letter-spacing: .05em;
  padding: 9px 15px; z-index: 45; box-shadow: 0 8px 24px rgba(0,0,0,.3);
}
.soundhint .sh-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--ylw); animation: bl 1.2s steps(1) infinite; }
@media (prefers-reduced-motion: reduce) { .soundhint .sh-dot { animation: none; } }
.toast { position: fixed; left: 50%; bottom: 26px; transform: translateX(-50%); background: var(--ink); color: var(--bg); font-size: 12px; letter-spacing: .06em; font-weight: 700; padding: 9px 16px; z-index: 50; display: none; font-family: var(--mono); }

@media (max-width: 700px) {
  .brmain { grid-template-columns: 26px 1fr 66px 78px; gap: 9px; padding-left: 10px; }
  .brow .bar { display: none; }
}
@media (max-width: 620px) {
  body { font-size: 14px; }
  .match { grid-template-columns: 1fr 64px 1fr 36px; gap: 6px; font-size: 13px; padding: 8px 9px; }
  .match .cl { font-size: 10px; }
  .orow { grid-template-columns: 1fr 70px 52px; }
  .h2hrow { grid-template-columns: 42px 1fr 42px; }
  .h2hrow > :nth-child(3), .h2hrow > :nth-child(4) { display: none; }
  .h2hscore { gap: 8px; padding: 12px 10px; }
  .h2hscore .num { font-size: 25px; }
  .h2hscore .who { font-size: 13px; }
}

/* ===================== SKIN (last, so it overrides the base) ===================== */
__SKIN_CSS__
</style>
</head>
<body>
<div class="toast" id="toast"></div>
<div class="page">

  <div class="strip">
    <span class="pageno" id="mwchip">&nbsp;</span>
    <span class="spacer"></span>
    <button type="button" class="tbtn" id="fxbtn" aria-pressed="true" title="Air horn, crowd and a ball in the net when a goal goes in">FX ON</button>
    <span class="seg" role="group" aria-label="Theme">
      <button type="button" data-theme="light" aria-pressed="false">LIGHT</button>
      <button type="button" data-theme="dark" aria-pressed="false">DARK</button>
      <button type="button" data-theme="auto" aria-pressed="true">AUTO</button>
    </span>
    <span class="clock"><span class="d" id="cdate">--- -- ---</span> <span id="ctime">--:--:--</span></span>
  </div>
  <div class="rainbow"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>

  <header class="mast">
    <div class="mast-grid">
      <div class="mast-main">
        <h1><a href="." aria-label="Back to the top">__MAST__</a></h1>
        <p class="tag">Eleven of us wrote down how the Premier League would finish. Every club
           scores the gap between the place you gave it and the place it actually holds; add up
           all twenty and the <b>lowest total wins</b>. It rescores itself while games are on.</p>
      </div>
      <aside class="factsbox" id="factsbox" aria-live="polite">
        <div class="factshd">Did you know</div>
        <ul class="factslist" id="factslist"></ul>
      </aside>
    </div>
  </header>

  <div id="notice"></div>

  <section class="sec">
    <div class="sechead">
      <h2>THE RECKONING</h2>
      <span class="hint">click a name for the full card &middot; LINK copies a shareable URL</span>
    </div>
    <div class="board" id="board"></div>
  </section>

  <section class="sec" id="secmatches" hidden>
    <div class="sechead">
      <h2 class="m" id="mtitle">FIXTURES</h2>
      <span class="hint" id="mhint"></span>
    </div>
    <div class="ticker">
      <div class="thead"><span id="tlabel">FIXTURES</span></div>
      <div id="matches"></div>
    </div>
    <div id="goalreport"></div>
  </section>

  <section class="sec" id="secrace">
    <div class="sechead">
      <h2 class="o">THE SEASON RACE</h2>
      <span class="hint">lower is better &middot; hover the chart for any matchday</span>
    </div>
    <div id="race"><div class="pending">LOADING SEASON HISTORY&hellip;</div></div>
  </section>

  <section class="sec" id="sectable">
    <div class="sechead">
      <h2 class="y">AS IT STANDS</h2>
      <span class="hint" id="tabhint"></span>
    </div>
    <div class="scroll">
      <table class="lg">
        <thead><tr>
          <th>#</th><th></th><th>CLUB</th><th>P</th><th>W</th><th>D</th><th>L</th><th>GD</th><th>PTS</th>
        </tr></thead>
        <tbody id="ltable"></tbody>
      </table>
    </div>
  </section>

  <section class="sec" id="sech2h">
    <div class="sechead">
      <h2 class="g">HEAD TO HEAD</h2>
      <span class="hint">totals, who leads, and where you disagree most</span>
    </div>
    <div class="h2hpick">
      <select id="h2hA" aria-label="First player"></select>
      <span>versus</span>
      <select id="h2hB" aria-label="Second player"></select>
      <button type="button" class="tbtn" id="h2hcopy">COPY LINK</button>
    </div>
    <div class="h2hcard" id="h2h"></div>
  </section>

  <section class="sec" id="secgrid">
    <div class="sechead">
      <h2 class="g">WHO BACKED WHOM</h2>
      <span class="hint">everyone's predicted finish for every club</span>
    </div>
    <div class="scroll">
      <table class="gr">
        <thead><tr id="ghead"></tr></thead>
        <tbody id="gbody"></tbody>
      </table>
    </div>
    <div class="legend" id="gridlegend"></div>
  </section>

  <section class="sec" id="secdamage">
    <div class="sechead">
      <h2 class="m">DAMAGE REPORT</h2>
      <span class="hint">the clubs doing the most harm, and who they are hurting</span>
    </div>
    <div class="scroll">
      <table class="dm">
        <thead><tr>
          <th>CLUB</th><th>NOW</th><th>PAIN</th><th>WORST HIT</th>
        </tr></thead>
        <tbody id="dbody"></tbody>
      </table>
    </div>
  </section>

  <section class="sec" id="secodds">
    <div class="sechead">
      <h2 class="v">TITLE ODDS</h2>
      <span class="hint" id="oddshint">simulating the rest of the season</span>
    </div>
    <div id="odds"><div class="pending">WAITING ON SEASON DATA&hellip;</div></div>
  </section>

  <section class="sec" id="secpot">
    <div class="sechead">
      <h2 class="y">THE POT</h2>
      <span class="hint" id="pothint"></span>
    </div>
    <div class="pot" id="pot"></div>
    <div class="potnote" id="potnote"></div>
  </section>

  <div class="status">
    <span id="stat">CONNECTING&hellip;</span>
    <span>DATA ESPN &middot; REFRESHES EVERY 60s WHILE GAMES ARE ON</span>
  </div>

</div>
<script>
(function () {
  "use strict";

  var PRED    = __PREDICTIONS__;
  var PENDING = __PENDING__;
  var TEAMS   = __TEAMS__;
  var SHORT   = __SHORT__;
  var FULL    = __FULL__;
  var MONEY   = __MONEY__;
  var BADGE   = __BADGES__;          /* club -> data URI, or {} when the skin has none */

  var STANDINGS = "https://site.api.espn.com/apis/v2/sports/soccer/eng.1/standings";
  var SCORES    = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard?dates=";
  var SEASON    = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard?limit=500&dates=20260801-20270601";

  var NAMES = Object.keys(PRED).sort();
  var CLUBS = Object.keys(SHORT);
  var LIVE_MS = 60000, IDLE_MS = 600000;
  var SIMS = 2000;

  var lastScores = {}, goalAt = {}, openCards = {};
  var prevTotals = null, prevPos = null, prevLeader = null;
  var hasData = false, seasonTried = false, seasonFixtures = null, factsShown = false;
  var timer = null, currentList = null, currentScored = null, history = null;
  var fxOn = true, audioReady = false;
  var wantPlayer = null;   /* ?p=<name>, scrolled to once the board first renders */
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- helpers ---------- */
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = String(text);
    return n;
  }
  function svgEl(tag, attrs) {
    var n = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function money(n) { return "$" + n; }
  function ordinal(n) {
    var s = ["th", "st", "nd", "rd"], v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
  }
  function gapClass(g) {
    if (g === 0) return "g0";
    if (g <= 2)  return "g1";
    if (g <= 5)  return "g2";
    if (g <= 9)  return "g3";
    return "g4";
  }
  function tok(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }
  function playerColor(i) { return tok("--p" + ((i % 11) + 1)); }
  function badge(club, cls) {
    if (!BADGE[club]) return null;
    var i = el("img");
    i.src = BADGE[club];
    i.alt = "";
    i.className = "bdgimg" + (cls ? " " + cls : "") + (darkNow() ? " badgeplate" : "");
    return i;
  }
  function darkNow() {
    var stamped = document.documentElement.getAttribute("data-theme");
    if (stamped === "dark") return true;
    if (stamped === "light") return false;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function toast(msg) {
    var t = document.getElementById("toast");
    t.textContent = msg;
    t.style.display = "block";
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { t.style.display = "none"; }, 1800);
  }

  /* ---------- theme ---------- */
  var themeBtns = document.querySelectorAll(".seg button");
  function applyTheme(mode) {
    if (mode === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", mode);
    themeBtns.forEach(function (b) {
      b.setAttribute("aria-pressed", b.dataset.theme === mode ? "true" : "false");
    });
    try { localStorage.setItem("tt-theme", mode); } catch (e) {}
    var dark = darkNow();
    document.querySelectorAll("img.bdgimg").forEach(function (i) {
      i.classList.toggle("badgeplate", dark);
    });
    if (history) renderRace(history);
    renderOdds();
    renderH2H();
    renderLegend();
  }
  var savedTheme = "auto";
  try { savedTheme = localStorage.getItem("tt-theme") || "auto"; } catch (e) {}
  themeBtns.forEach(function (b) {
    b.addEventListener("click", function () { applyTheme(b.dataset.theme); });
  });

  /* ---------- clock ---------- */
  var DAYS = ["SUN","MON","TUE","WED","THU","FRI","SAT"];
  var MONS = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"];
  function tickClock() {
    var d = new Date();
    document.getElementById("cdate").textContent = DAYS[d.getDay()] + " " + pad(d.getDate()) + " " + MONS[d.getMonth()];
    document.getElementById("ctime").textContent = pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds());
  }
  tickClock();
  setInterval(tickClock, 1000);

  /* =====================================================================
     GOAL EFFECTS — kick, net, crowd, and a ball buried in the top corner
     ===================================================================== */
  var fxBtn = document.getElementById("fxbtn");
  try {
    var savedFx = localStorage.getItem("tt-fx");
    if (savedFx !== null) fxOn = savedFx === "1";
  } catch (e) {}
  function paintFx() {
    fxBtn.setAttribute("aria-pressed", fxOn ? "true" : "false");
    fxBtn.textContent = "FX " + (fxOn ? "ON" : "OFF");
  }
  paintFx();
  fxBtn.addEventListener("click", function () {
    fxOn = !fxOn;
    try { localStorage.setItem("tt-fx", fxOn ? "1" : "0"); } catch (e) {}
    paintFx();
    if (fxOn) { armAudio(); celebrate("FX ON"); }
  });

  /* ---- sound: decoded once into buffers, so playback never stalls or
     rejects, and overlapping goals layer instead of cutting each other off ---- */
  var actx = null, crowdBuf = null;
  function ctx() {
    if (!actx) {
      try { actx = new (window.AudioContext || window.webkitAudioContext)(); }
      catch (e) { return null; }
    }
    return actx;
  }
  function decodeCrowd() {
    var c = ctx();
    if (!c || crowdBuf) return;
    try {
      var b64 = "__CROWD__".split(",")[1];
      var bin = atob(b64), arr = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
      c.decodeAudioData(arr.buffer,
        function (buf) { crowdBuf = buf; },
        function () {});
    } catch (e) {}
  }
  decodeCrowd();                       /* a suspended context still decodes */

  /* Playback needs a real gesture; decoding does not. */
  function armAudio() {
    if (audioReady) return;
    audioReady = true;
    var c = ctx();
    if (c && c.state === "suspended") c.resume();
    decodeCrowd();
    hideSoundHint();
  }
  ["pointerdown", "keydown", "touchstart", "click"].forEach(function (ev) {
    window.addEventListener(ev, armAudio, { once: true, passive: true });
  });

  /* Browsers will not let a page make noise before the visitor has clicked, so
     rather than failing silently, say so. */
  var hintEl = null;
  function showSoundHint() {
    if (!fxOn || audioReady || hintEl) return;
    hintEl = el("div", "soundhint");
    hintEl.appendChild(el("span", "sh-dot"));
    hintEl.appendChild(document.createTextNode("Click anywhere to turn the goal sounds on"));
    document.body.appendChild(hintEl);
  }
  function hideSoundHint() { if (hintEl) { hintEl.remove(); hintEl = null; } }

  function noiseBuffer(c, secs) {
    var n = Math.floor(c.sampleRate * secs);
    var buf = c.createBuffer(1, n, c.sampleRate);
    var d = buf.getChannelData(0);
    for (var i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
    return buf;
  }

  /* boot on ball: low thump with a sharp leading edge */
  function sfxKick(at) {
    var c = ctx(); if (!c) return;
    var t = c.currentTime + at;
    var o = c.createOscillator(), g = c.createGain();
    o.type = "sine";
    o.frequency.setValueAtTime(170, t);
    o.frequency.exponentialRampToValueAtTime(48, t + 0.13);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.75, t + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.19);
    o.connect(g); g.connect(c.destination);
    o.start(t); o.stop(t + 0.2);

    var sn = c.createBufferSource(), sg = c.createGain(), hp = c.createBiquadFilter();
    sn.buffer = noiseBuffer(c, 0.06);
    hp.type = "highpass"; hp.frequency.value = 1400;
    sg.gain.setValueAtTime(0.5, t);
    sg.gain.exponentialRampToValueAtTime(0.0001, t + 0.055);
    sn.connect(hp); hp.connect(sg); sg.connect(c.destination);
    sn.start(t);
  }

  /* ball into netting: bright rustle, fast decay */
  function sfxNet(at) {
    var c = ctx(); if (!c) return;
    var t = c.currentTime + at;
    var sn = c.createBufferSource(), bp = c.createBiquadFilter(), g = c.createGain();
    sn.buffer = noiseBuffer(c, 0.4);
    bp.type = "bandpass";
    bp.frequency.setValueAtTime(2600, t);
    bp.frequency.exponentialRampToValueAtTime(900, t + 0.3);
    bp.Q.value = 0.8;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.42, t + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.34);
    sn.connect(bp); bp.connect(g); g.connect(c.destination);
    sn.start(t);
  }

  function sfxCrowd(at) {
    var c = ctx();
    if (!c || !crowdBuf) return;
    var sn = c.createBufferSource(), g = c.createGain();
    sn.buffer = crowdBuf;
    g.gain.value = 0.55;
    sn.connect(g); g.connect(c.destination);
    sn.start(c.currentTime + at);
  }

  function goalSound() {
    if (!fxOn) return;
    var c = ctx();
    if (!c) return;
    /* scheduling into a suspended context loses the sounds, so ask instead */
    if (c.state !== "running") { c.resume(); showSoundHint(); return; }
    sfxKick(0);
    sfxNet(0.52);
    sfxCrowd(0.60);
  }

  /* ---- the celebration: real elements and CSS, not a hand-drawn canvas ---- */
  var BALL_SVG =
    '<svg viewBox="0 0 100 100" aria-hidden="true">' +
      '<defs><radialGradient id="bs" cx="36%" cy="30%" r="72%">' +
        '<stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#c9cdd2"/>' +
      '</radialGradient></defs>' +
      '<circle cx="50" cy="50" r="47" fill="url(#bs)" stroke="#1a1c20" stroke-width="2.5"/>' +
      '<path fill="#1a1c20" d="M50 22l13.5 9.8-5.2 15.9H41.7l-5.2-15.9z"/>' +
      '<path fill="#1a1c20" d="M23.2 44.4l12.2 4.2 1.1 16.6-13.1 4.9-7.3-11.1z"/>' +
      '<path fill="#1a1c20" d="M76.8 44.4l7.1 14.6-7.3 11.1-13.1-4.9 1.1-16.6z"/>' +
      '<path fill="#1a1c20" d="M39.5 71.2h21l4.4 13.3-7.5 5.2h-14.8l-7.5-5.2z"/>' +
    '</svg>';

  var GOAL_SVG =
    '<svg viewBox="0 0 420 260" aria-hidden="true" class="net">' +
      '<defs><pattern id="mesh" width="13" height="13" patternUnits="userSpaceOnUse">' +
        '<path d="M13 0H0v13" fill="none" stroke="currentColor" stroke-width="1" opacity=".42"/>' +
      '</pattern></defs>' +
      '<path d="M14 246 L74 196 H406 V26 L346 76" fill="none" stroke="currentColor" ' +
        'stroke-width="2" opacity=".5"/>' +
      '<rect x="14" y="76" width="332" height="170" fill="url(#mesh)"/>' +
      '<rect x="14" y="76" width="332" height="170" fill="none" stroke="currentColor" ' +
        'stroke-width="7" stroke-linejoin="round"/>' +
    '</svg>';

  function celebrate(label) {
    if (!fxOn) return;
    goalSound();
    if (reduceMotion || document.hidden) return;

    var old = document.getElementById("cel");
    if (old) old.remove();

    var cel = el("div", "cel");
    cel.id = "cel";
    cel.innerHTML =
      '<div class="cel-scrim"></div>' +
      '<div class="cel-band">' +
        '<div class="cel-text">' +
          '<div class="cel-word">GOAL<span>!</span></div>' +
          '<div class="cel-line"></div>' +
        '</div>' +
        '<div class="cel-goal">' + GOAL_SVG + '</div>' +
        '<div class="cel-ball">' + BALL_SVG + '</div>' +
      '</div>';
    cel.querySelector(".cel-line").textContent = label || "";
    document.body.appendChild(cel);
    var kill = setTimeout(function () { if (cel.parentNode) cel.remove(); }, 8200);
    /* Clicking anywhere outside the banner closes it early. Armed once the wipe
       has finished — until then the banner is still clipped, so a stray click
       over it would fall through to the scrim and shut it straight away. */
    setTimeout(function () {
      cel.querySelector(".cel-scrim").addEventListener("click", function () {
        clearTimeout(kill);
        if (cel.parentNode) cel.remove();
      });
    }, 500);
  }

  /* ---------- scoring ---------- */
  function scoreEveryone(posByTeam) {
    var out = NAMES.map(function (name) {
      var picks = [], total = 0, exact = 0, worst = null;
      Object.keys(PRED[name]).forEach(function (team) {
        var pred = PRED[name][team], real = posByTeam[team];
        var gap = Math.abs(pred - real);
        total += gap;
        if (gap === 0) exact++;
        var p = { team: team, pred: pred, real: real, gap: gap, dir: real - pred };
        if (!worst || gap > worst.gap) worst = p;
        picks.push(p);
      });
      picks.sort(function (a, b) { return a.pred - b.pred; });
      return { name: name, total: total, exact: exact, worst: worst, picks: picks };
    });
    out.sort(function (a, b) { return a.total - b.total || a.name.localeCompare(b.name); });
    var rank = 0, prev = null;
    out.forEach(function (p, i) {
      if (p.total !== prev) { rank = i + 1; prev = p.total; }
      p.rank = rank;
    });
    return out;
  }
  function totalsFor(posByTeam) {
    var t = {};
    NAMES.forEach(function (n) {
      var s = 0;
      Object.keys(PRED[n]).forEach(function (team) { s += Math.abs(PRED[n][team] - posByTeam[team]); });
      t[n] = s;
    });
    return t;
  }

  /* ---------- espn parsing ---------- */
  function statVal(stats, key) {
    for (var i = 0; i < stats.length; i++) if (stats[i].name === key) return Number(stats[i].value) || 0;
    return 0;
  }
  function parseStandings(json) {
    var kids = json && json.children;
    if (!kids || !kids.length) throw new Error("no standings group");
    var entries = kids[0].standings.entries;
    if (!entries || entries.length !== 20) throw new Error("expected 20 clubs, got " + (entries ? entries.length : 0));
    var rows = {};
    entries.forEach(function (e) {
      var name = TEAMS[String(e.team.id)];
      if (!name) throw new Error("unknown club id " + e.team.id);
      rows[name] = {
        team: name,
        pld: statVal(e.stats, "gamesPlayed"), w: statVal(e.stats, "wins"),
        d: statVal(e.stats, "ties"), l: statVal(e.stats, "losses"),
        gf: statVal(e.stats, "pointsFor"), ga: statVal(e.stats, "pointsAgainst"),
        pts: statVal(e.stats, "points"), live: false
      };
    });
    if (Object.keys(rows).length !== 20) throw new Error("club mapping incomplete");
    return rows;
  }
  function parseMatches(json) {
    var evs = (json && json.events) || [], out = [];
    evs.forEach(function (e) {
      var c = e.competitions && e.competitions[0];
      if (!c) return;
      var home = null, away = null;
      c.competitors.forEach(function (t) {
        var rec = { id: String(t.team.id), name: TEAMS[String(t.team.id)], goals: Number(t.score) || 0 };
        if (t.homeAway === "home") home = rec; else away = rec;
      });
      if (!home || !away || !home.name || !away.name) return;
      var st = (e.status && e.status.type) || {};
      out.push({
        id: String(e.id), date: e.date, home: home, away: away,
        state: st.state, clock: (e.status && e.status.displayClock) || "",
        detail: st.shortDetail || st.detail || ""
      });
    });
    out.sort(function (a, b) { return new Date(a.date) - new Date(b.date); });
    return out;
  }
  function applyLive(rows, matches) {
    matches.forEach(function (m) {
      if (m.state !== "in") return;
      var h = rows[m.home.name], a = rows[m.away.name];
      if (!h || !a) return;
      if (h.pld >= 38 || a.pld >= 38) return;
      h.live = a.live = true;
      h.pld++; a.pld++;
      h.gf += m.home.goals; h.ga += m.away.goals;
      a.gf += m.away.goals; a.ga += m.home.goals;
      if (m.home.goals > m.away.goals)      { h.w++; h.pts += 3; a.l++; }
      else if (m.home.goals < m.away.goals) { a.w++; a.pts += 3; h.l++; }
      else                                  { h.d++; a.d++; h.pts++; a.pts++; }
    });
    return rows;
  }
  function orderTable(rows) {
    var list = Object.keys(rows).map(function (k) { return rows[k]; });
    list.forEach(function (r) { r.gd = r.gf - r.ga; });
    list.sort(function (a, b) { return b.pts - a.pts || b.gd - a.gd || b.gf - a.gf || a.team.localeCompare(b.team); });
    list.forEach(function (r, i) { r.pos = i + 1; });
    return list;
  }

  /* ---------- pot ---------- */
  function renderPot(scored) {
    var box = document.getElementById("pot");
    clear(box);
    [{ k: "POT", v: money(MONEY.pot), cls: "" },
     { k: "1ST", v: money(MONEY.prizes[0]), cls: "p1" },
     { k: "2ND", v: money(MONEY.prizes[1]), cls: "p2" },
     { k: "3RD", v: money(MONEY.prizes[2]), cls: "p3" }].forEach(function (c) {
      var d = el("div", "potcell " + c.cls);
      d.appendChild(el("div", "k", c.k));
      d.appendChild(el("div", "v", c.v));
      if (c.cls && scored) {
        var place = Number(c.cls.slice(1));
        var holder = scored.filter(function (p) { return p.rank === place; });
        d.appendChild(el("div", "k", holder.length
          ? holder.map(function (p) { return p.name; }).join(" / ") : "—"));
      }
      box.appendChild(d);
    });
    document.getElementById("pothint").textContent =
      money(MONEY.buyIn) + " each × " + MONEY.players + " players";
    var note = document.getElementById("potnote");
    clear(note);
    if (PENDING.length) {
      note.appendChild(document.createTextNode("Still to submit a table: "));
      note.appendChild(el("b", null, PENDING.join(", ")));
      note.appendChild(document.createTextNode(
        ". They are in the pot but cannot be scored until their picks land."));
    }
  }

  /* ---------- vidiprinter ---------- */
  function renderMatches(matches) {
    var sec = document.getElementById("secmatches");
    var wrap = document.getElementById("matches");
    var live = matches.filter(function (m) { return m.state === "in"; });
    var soon = matches.filter(function (m) { return m.state === "pre"; });
    var done = matches.filter(function (m) { return m.state === "post"; });
    var show = live.length ? live : (done.length ? done.slice(-6).concat(soon.slice(0, 4)) : soon.slice(0, 6));
    if (!show.length) { sec.hidden = true; return; }
    sec.hidden = false;

    var lbl = document.getElementById("tlabel");
    clear(lbl);
    if (live.length) {
      lbl.appendChild(el("span", "blink", "● LIVE"));
      lbl.appendChild(document.createTextNode("  " + live.length + " MATCH" + (live.length > 1 ? "ES" : "") + " IN PLAY"));
      document.getElementById("mtitle").textContent = "VIDIPRINTER";
      document.getElementById("mhint").textContent = "table updates as goals go in";
    } else {
      lbl.appendChild(document.createTextNode(done.length ? "LATEST RESULTS & NEXT UP" : "COMING UP"));
      document.getElementById("mtitle").textContent = "FIXTURES";
      document.getElementById("mhint").textContent = "";
    }

    clear(wrap);
    show.forEach(function (m) {
      var row = el("div", "match " + m.state);
      var since = goalAt[m.id] ? Date.now() - goalAt[m.id] : Infinity;
      if (since < 90000) row.classList.add("goal");
      if (since < 25000) row.classList.add("fresh");

      function side(cls, club) {
        var s = el("span", cls);
        var bd = el("span", "bd");
        var im = badge(club);
        if (im) bd.appendChild(im);
        bd.appendChild(el("span", null, SHORT[club]));
        s.appendChild(bd);
        return s;
      }
      row.appendChild(side("h", m.home.name));
      var sc = el("span", "sc");
      if (m.state === "pre") {
        var kd = new Date(m.date);
        sc.appendChild(el("span", "scdate", DAYS[kd.getDay()] + " " + kd.getDate() + " " + MONS[kd.getMonth()]));
        sc.appendChild(el("span", "sctime",
          kd.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true })));
      } else {
        sc.textContent = m.home.goals + "-" + m.away.goals;
      }
      row.appendChild(sc);
      row.appendChild(side("a", m.away.name));
      var cl = el("span", "cl");
      if (since < 25000) cl.appendChild(el("span", "gl", "GOAL"));
      else if (m.state === "in") cl.textContent = m.clock || m.detail;
      else if (m.state === "post") cl.textContent = "FT";
      row.appendChild(cl);
      wrap.appendChild(row);
    });
  }

  /* ---------- goal report ---------- */
  function renderGoalReport(ev, totals, posNow, scored) {
    var box = document.getElementById("goalreport");
    clear(box);
    if (!ev || !prevTotals || !prevPos) return;

    var card = el("div", "goalcard");
    var gh = el("div", "gh");
    gh.appendChild(document.createTextNode(
      "GOAL · " + SHORT[ev.home.name] + " " + ev.home.goals + "-" + ev.away.goals +
      " " + SHORT[ev.away.name] + (ev.clock ? "  " + ev.clock : "")));
    var close = el("button", "gclose", "DISMISS");
    close.type = "button";
    close.addEventListener("click", function () { clear(box); });
    gh.appendChild(close);
    card.appendChild(gh);

    var gb = el("div", "gb");
    var moved = [];
    Object.keys(posNow).forEach(function (t) {
      if (prevPos[t] && prevPos[t] !== posNow[t]) moved.push({ team: t, from: prevPos[t], to: posNow[t] });
    });
    moved.sort(function (a, b) { return a.to - b.to; });

    var r1 = el("div", "grow");
    r1.appendChild(el("span", "lab", "TABLE"));
    if (!moved.length) r1.appendChild(el("span", "neu", "no change in the order"));
    else moved.slice(0, 6).forEach(function (m) {
      r1.appendChild(el("span", m.to < m.from ? "up" : "dn", SHORT[m.team] + " " + m.from + "→" + m.to));
    });
    gb.appendChild(r1);

    var deltas = NAMES.map(function (n) { return { name: n, d: totals[n] - prevTotals[n], now: totals[n] }; })
                      .filter(function (x) { return x.d !== 0; })
                      .sort(function (a, b) { return a.d - b.d; });
    var r2 = el("div", "grow");
    r2.appendChild(el("span", "lab", "SCORES ↓GOOD"));
    if (!deltas.length) r2.appendChild(el("span", "neu", "nobody moved"));
    else deltas.forEach(function (x) {
      r2.appendChild(el("span", x.d < 0 ? "up" : "dn",
        x.name + " " + x.now + " (" + (x.d > 0 ? "+" : "") + x.d + ")"));
    });
    gb.appendChild(r2);

    var leader = scored.length ? scored[0].name : null;
    var r3 = el("div", "grow");
    r3.appendChild(el("span", "lab", "LEAD"));
    if (leader && prevLeader && leader !== prevLeader) {
      r3.appendChild(el("span", "crown", leader + " takes the lead from " + prevLeader));
    } else if (leader) {
      var second = scored.filter(function (p) { return p.rank > 1; })[0];
      r3.appendChild(el("span", "neu", leader + " still ahead" +
        (second ? " by " + (second.total - scored[0].total) : "")));
    }
    gb.appendChild(r3);
    card.appendChild(gb);
    box.appendChild(card);
  }

  /* ---------- leaderboard ---------- */
  function buildBlankPicks(name) {
    return Object.keys(PRED[name])
      .map(function (t) { return { team: t, pred: PRED[name][t], gap: null, dir: null }; })
      .sort(function (a, b) { return a.pred - b.pred; });
  }

  function renderBoard(scored, started) {
    var board = document.getElementById("board");
    clear(board);
    if (started) {
      var lead = scored[0].total;
      var span = Math.max(1, scored[scored.length - 1].total - lead);
      scored.forEach(function (p) {
        var cls = "brow" + (p.rank === 1 ? " lead" : "");
        if (p.rank <= 3) cls += " m" + p.rank;
        var row = mkRow(cls, p.name, {
          pos: p.rank, behind: p.total - lead, span: span, tot: p.total,
          meta: p.rank === 1 ? "LEADER" : "+" + (p.total - lead),
          cash: p.rank <= 3 ? money(MONEY.prizes[p.rank - 1]) : null
        });
        board.appendChild(row.wrap);
        attachCard(board, row, p, true, p.name);
      });
    } else {
      NAMES.forEach(function (name) {
        var row = mkRow("brow", name, { pos: "–", behind: null, tot: "–", meta: "TO PLAY", cash: null });
        board.appendChild(row.wrap);
        attachCard(board, row, { picks: buildBlankPicks(name) }, false, name);
      });
    }
    PENDING.forEach(function (name) {
      var row = mkRow("brow noentry", name,
        { pos: "–", behind: null, tot: "–", meta: "NO ENTRY YET", cash: null }, true);
      board.appendChild(row.wrap);
    });
  }

  function mkRow(cls, name, v, noCopy) {
    var wrap = el("div", cls);
    wrap.dataset.player = name;
    var main = el("button", "brmain");
    main.type = "button";
    main.appendChild(el("span", "pos", v.pos));
    main.appendChild(el("span", "nm", name));

    var bar = el("span", "bar");
    if (v.behind !== null && v.behind !== undefined) {
      var filled = Math.round((v.behind / v.span) * 18);
      var blocks = el("b", null, "█".repeat(filled) + "░".repeat(18 - filled));
      blocks.style.color = "";
      bar.appendChild(blocks);
      var track = el("i");
      var fill = el("em");
      fill.style.width = Math.max(v.behind === 0 ? 0 : 3, (v.behind / v.span) * 100) + "%";
      track.appendChild(fill);
      bar.appendChild(track);
    }
    main.appendChild(bar);

    main.appendChild(el("span", "tot", v.tot));
    var meta = el("span", "meta");
    meta.appendChild(document.createTextNode(v.meta));
    if (v.cash) meta.appendChild(el("span", "cash", v.cash));
    main.appendChild(meta);
    wrap.appendChild(main);

    if (!noCopy) {
      var cp = el("button", "brcopy", "LINK");
      cp.type = "button";
      cp.title = "Copy a link straight to " + name + "'s card";
      cp.setAttribute("aria-label", "Copy link to " + name + "'s card");
      cp.addEventListener("click", function (e) {
        e.stopPropagation();
        var url = location.origin + location.pathname + "?p=" + encodeURIComponent(name);
        copy(url, function (ok) {
          cp.textContent = ok ? "COPIED" : "NO CLIPBOARD";
          cp.classList.toggle("done", ok);
          toast(ok ? name + "'s link copied" : "Couldn't reach the clipboard — the link is " + url);
          setTimeout(function () { cp.textContent = "LINK"; cp.classList.remove("done"); }, 2000);
        });
      });
      wrap.appendChild(cp);
    } else {
      wrap.appendChild(el("span", "brcopy", ""));
    }
    return { wrap: wrap, main: main };
  }

  function copy(text, done) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { done(true); }, fallback);
    } else fallback();
    function fallback() {
      try {
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed"; ta.style.top = "-999px"; ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        ta.setSelectionRange(0, text.length);
        var ok = document.execCommand("copy");
        document.body.removeChild(ta);
        done(ok);
      } catch (e) { done(false); }
    }
  }

  var PKHEAD = ["#", "CLUB", "MOVE", "GAP"];

  function attachCard(board, row, p, started, name) {
    var card = el("div", "card");
    card.hidden = !openCards[name];
    row.wrap.classList.toggle("open", !!openCards[name]);

    if (started) {
      var kpis = el("div", "kpis");
      [["SPOT ON", p.exact], ["AVG GAP", (p.total / 20).toFixed(1)],
       ["WORST CALL", SHORT[p.worst.team] + " " + p.worst.gap]].forEach(function (k) {
        var s = el("span");
        s.appendChild(document.createTextNode(k[0] + " "));
        s.appendChild(el("b", null, k[1]));
        kpis.appendChild(s);
      });
      card.appendChild(kpis);
    }

    /* four columns reading DOWN: 1-5, 6-10, 11-15, 16-20 */
    var cols = el("div", "pickcols");
    for (var c = 0; c < 4; c++) {
      var col = el("div", "pickcol");
      var head = el("div", "pkhead");
      PKHEAD.forEach(function (h) { head.appendChild(el("span", null, h)); });
      col.appendChild(head);
      p.picks.slice(c * 5, c * 5 + 5).forEach(function (k) {
        var r = el("div", "pk");
        r.appendChild(el("span", "n", k.pred));
        var t = el("span", "t");
        var im = badge(k.team);
        if (im) t.appendChild(im);
        t.appendChild(el("span", null, SHORT[k.team]));
        r.appendChild(t);
        r.appendChild(el("span", "m", k.dir === null ? "" :
          (k.dir === 0 ? "—" : (k.dir > 0 ? "↓" : "↑") + Math.abs(k.dir))));
        r.appendChild(el("span", "g " + (k.gap === null ? "" : gapClass(k.gap)), k.gap === null ? "" : k.gap));
        col.appendChild(r);
      });
      cols.appendChild(col);
    }
    card.appendChild(cols);
    board.appendChild(card);

    row.main.setAttribute("aria-expanded", openCards[name] ? "true" : "false");
    row.main.addEventListener("click", function () {
      var open = row.main.getAttribute("aria-expanded") === "true";
      row.main.setAttribute("aria-expanded", open ? "false" : "true");
      card.hidden = open;
      openCards[name] = !open;
      row.wrap.classList.toggle("open", !open);
    });
  }

  /* ---------- real table ---------- */
  function renderTable(list, started) {
    var tb = document.getElementById("ltable");
    clear(tb);
    list.forEach(function (r) {
      var tr = el("tr", (r.pos <= 5 ? "ucl" : (r.pos >= 18 ? "rel" : "")) + (r.live ? " playing" : ""));
      tr.appendChild(el("td", "rk", r.pos));
      var bd = el("td", "bdg");
      var im = badge(r.team);
      if (im) bd.appendChild(im);
      tr.appendChild(bd);
      tr.appendChild(el("td", "cl", FULL[r.team]));
      [r.pld, r.w, r.d, r.l, (r.gd > 0 ? "+" : "") + r.gd].forEach(function (v) { tr.appendChild(el("td", null, v)); });
      tr.appendChild(el("td", "pt", r.pts));
      tb.appendChild(tr);
    });
    document.getElementById("tabhint").textContent =
      started ? "top 5 and bottom 3 marked · ● = in play" : "kicks off 21 august";
    var mw = list.reduce(function (m, r) { return Math.max(m, r.pld); }, 0);
    document.getElementById("mwchip").textContent = started ? "Matchweek " + mw : "Pre-season";
  }

  /* ---------- who backed whom ---------- */
  var LEGEND = [
    ["g0", "spot on"], ["g1", "1–2 out"], ["g2", "3–5 out"],
    ["g3", "6–9 out"], ["g4", "10+ out"]
  ];
  function renderLegend() {
    var box = document.getElementById("gridlegend");
    if (!box) return;
    clear(box);
    if (!currentList || !currentList.some(function (r) { return r.pld > 0; })) {
      box.appendChild(el("span", null, "Colours appear once the season is under way."));
      return;
    }
    box.appendChild(el("span", null, "HOW FAR OUT:"));
    LEGEND.forEach(function (l) {
      var sp = el("span");
      var sw = el("i");
      sw.style.background = tok("--" + { g0: "grn", g1: "cyn", g2: "ink", g3: "ylw", g4: "red" }[l[0]]);
      sp.appendChild(sw);
      sp.appendChild(document.createTextNode(l[1]));
      box.appendChild(sp);
    });
    box.appendChild(el("span", null, "· number shown is what they predicted"));
  }

  function renderGrid(list, started) {
    var gh = document.getElementById("ghead"), gb = document.getElementById("gbody");
    clear(gh); clear(gb);
    gh.appendChild(el("th", null, "CLUB"));
    gh.appendChild(el("th", null, "NOW"));
    NAMES.forEach(function (n) { gh.appendChild(el("th", null, n)); });
    list.slice().sort(function (a, b) { return a.pos - b.pos; }).forEach(function (r) {
      var tr = el("tr");
      var td = el("td", "club");
      var cw = el("span", "cw");
      var im = badge(r.team);
      if (im) cw.appendChild(im);
      cw.appendChild(el("span", null, FULL[r.team]));
      td.appendChild(cw);
      tr.appendChild(td);
      tr.appendChild(el("td", "rk", started ? r.pos : "–"));
      NAMES.forEach(function (n) {
        var pred = PRED[n][r.team];
        tr.appendChild(el("td", started ? gapClass(Math.abs(pred - r.pos)) : null, pred));
      });
      gb.appendChild(tr);
    });
    renderLegend();
  }

  function renderDamage(list, started) {
    var sec = document.getElementById("secdamage");
    if (!started) { sec.hidden = true; return; }
    sec.hidden = false;
    var tb = document.getElementById("dbody");
    clear(tb);
    list.map(function (r) {
      var pain = 0, worst = null;
      NAMES.forEach(function (n) {
        var g = Math.abs(PRED[n][r.team] - r.pos);
        pain += g;
        if (!worst || g > worst.g) worst = { n: n, g: g, pred: PRED[n][r.team] };
      });
      return { team: r.team, pos: r.pos, pain: pain, worst: worst };
    }).sort(function (a, b) { return b.pain - a.pain; })
      .forEach(function (r) {
        var tr = el("tr");
        var td = el("td", "club");
        var cw = el("span", "cw");
        var im = badge(r.team);
        if (im) cw.appendChild(im);
        cw.appendChild(el("span", null, FULL[r.team]));
        td.appendChild(cw);
        tr.appendChild(td);
        tr.appendChild(el("td", "rk", r.pos));
        tr.appendChild(el("td", gapClass(Math.round(r.pain / NAMES.length)), r.pain));
        tr.appendChild(el("td", null, r.worst.n + " — picked " + r.worst.pred + ", costs " + r.worst.g));
        tb.appendChild(tr);
      });
  }

  /* ---------- head to head ---------- */
  var wantH2H = null;   /* ?h2h=A,B — applied once the section has real data */

  function resolveH2HLink() {
    var m = /[?&]h2h=([^&]+)/.exec(location.search);
    if (!m) return;
    var parts = decodeURIComponent(m[1]).split(/[,|]/).map(function (x) { return x.trim().toLowerCase(); });
    if (parts.length !== 2) return;
    var found = parts.map(function (want) {
      return NAMES.filter(function (n) { return n.toLowerCase() === want; })[0];
    });
    if (found[0] && found[1]) wantH2H = found;
  }

  function applyH2HLink() {
    if (!wantH2H) return false;
    document.getElementById("h2hA").value = wantH2H[0];
    document.getElementById("h2hB").value = wantH2H[1];
    wantH2H = null;
    renderH2H();
    var sec = document.getElementById("sech2h");
    setTimeout(function () {
      sec.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
      var card = document.getElementById("h2h");
      card.classList.add("flash");
      setTimeout(function () { card.classList.remove("flash"); }, 3400);
    }, 90);
    return true;
  }

  function initH2H() {
    [["h2hA", 0], ["h2hB", 1]].forEach(function (cfg) {
      var sel = document.getElementById(cfg[0]);
      clear(sel);
      NAMES.forEach(function (n, i) {
        var o = el("option", null, n);
        o.value = n;
        if (i === cfg[1]) o.selected = true;
        sel.appendChild(o);
      });
      sel.addEventListener("change", function () { renderH2H(); });
    });

    var copyBtn = document.getElementById("h2hcopy");
    copyBtn.addEventListener("click", function () {
      var A = document.getElementById("h2hA").value, B = document.getElementById("h2hB").value;
      var url = location.origin + location.pathname + "?h2h=" +
                encodeURIComponent(A) + "," + encodeURIComponent(B);
      copy(url, function (ok) {
        copyBtn.textContent = ok ? "COPIED" : "NO CLIPBOARD";
        toast(ok ? "Link to " + A + " vs " + B + " copied" : "Couldn't reach the clipboard — the link is " + url);
        setTimeout(function () { copyBtn.textContent = "COPY LINK"; }, 2000);
      });
    });
  }

  function renderH2H() {
    var sec = document.getElementById("sech2h");
    var list = currentList;
    if (!list || !list.some(function (r) { return r.pld > 0; })) { sec.hidden = true; return; }
    sec.hidden = false;

    var A = document.getElementById("h2hA").value, B = document.getElementById("h2hB").value;
    var box = document.getElementById("h2h");
    clear(box);

    var byName = {};
    (currentScored || []).forEach(function (p) { byName[p.name] = p; });
    var pa = byName[A], pb = byName[B];
    if (!pa || !pb) { box.appendChild(el("div", "pending", "No scores yet.")); return; }

    var ca = playerColor(NAMES.indexOf(A)), cb = playerColor(NAMES.indexOf(B));

    var head = el("div", "h2hscore");
    function side(p, col, right) {
      var d = el("div", "side" + (right ? " r" : ""));
      var who = el("div", "who", p.name);
      who.style.color = col;
      d.appendChild(who);
      d.appendChild(el("div", "num", p.total));
      d.appendChild(el("div", "sub", "rank " + p.rank + " · " + p.exact + " spot on"));
      return d;
    }
    head.appendChild(side(pa, ca, false));
    var mid = el("div", "mid");
    var diff = Math.abs(pa.total - pb.total);
    mid.appendChild(document.createTextNode(diff === 0 ? "DEAD LEVEL" : "GAP"));
    if (diff !== 0) mid.appendChild(el("b", "win", (pa.total < pb.total ? A : B) + " −" + diff));
    head.appendChild(mid);
    head.appendChild(side(pb, cb, true));
    box.appendChild(head);

    var winA = 0, winB = 0, tie = 0;
    var rows = list.map(function (r) {
      var ga = Math.abs(PRED[A][r.team] - r.pos), gb = Math.abs(PRED[B][r.team] - r.pos);
      if (ga < gb) winA++; else if (gb < ga) winB++; else tie++;
      return { team: r.team, pos: r.pos, ga: ga, gb: gb, edge: gb - ga };
    });

    var bar = el("div", "h2hbar");
    [[winA, ca], [tie, tok("--dim")], [winB, cb]].forEach(function (seg) {
      var i = el("i");
      i.style.width = (seg[0] / 20 * 100) + "%";
      i.style.background = seg[1];
      bar.appendChild(i);
    });
    box.appendChild(bar);

    var counts = el("div", "h2hcount");
    function tally(label, n, col) {
      var sp = el("span");
      var b = el("b", null, n);
      if (col) b.style.color = col;
      sp.appendChild(b);
      sp.appendChild(document.createTextNode(" " + label));
      return sp;
    }
    counts.appendChild(tally(A + " closer", winA, ca));
    counts.appendChild(tally("same gap", tie, null));
    counts.appendChild(tally(B + " closer", winB, cb));
    box.appendChild(counts);

    var hd = el("div", "h2hrow hd");
    hd.appendChild(el("span", "lft", A));
    hd.appendChild(el("span", "club", "CLUB"));
    hd.appendChild(el("span", "v", "NOW"));
    hd.appendChild(el("span", "rgt", "EDGE"));
    hd.appendChild(el("span", "v", B));
    box.appendChild(hd);

    var top = rows.filter(function (r) { return r.edge !== 0; })
                  .sort(function (a, b) { return Math.abs(b.edge) - Math.abs(a.edge); })
                  .slice(0, 10);
    if (!top.length) { box.appendChild(el("div", "pending", "Level on all twenty clubs.")); return; }
    top.forEach(function (r) {
      var tr = el("div", "h2hrow");
      tr.appendChild(el("span", "v lft " + gapClass(r.ga), r.ga));
      var cl = el("span", "club");
      var im = badge(r.team);
      if (im) cl.appendChild(im);
      cl.appendChild(el("span", null, SHORT[r.team]));
      tr.appendChild(cl);
      tr.appendChild(el("span", "v rk", r.pos));
      var w = el("span", "who rgt", (r.edge > 0 ? A : B) + " +" + Math.abs(r.edge));
      w.style.color = r.edge > 0 ? ca : cb;
      tr.appendChild(w);
      tr.appendChild(el("span", "v " + gapClass(r.gb), r.gb));
      box.appendChild(tr);
    });
  }

  /* ---------- season history ---------- */
  function buildHistory(fixtures) {
    var done = fixtures.filter(function (m) { return m.state === "post"; });
    if (done.length < 20) return null;
    var rows = {};
    Object.keys(TEAMS).forEach(function (id) {
      rows[TEAMS[id]] = { team: TEAMS[id], pld: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0, pts: 0 };
    });
    var series = {}, dates = [], top3 = [];
    NAMES.forEach(function (n) { series[n] = []; });
    var i = 0;
    while (i < done.length) {
      var day = done[i].date.slice(0, 10);
      while (i < done.length && done[i].date.slice(0, 10) === day) {
        var m = done[i], h = rows[m.home.name], a = rows[m.away.name];
        if (h && a) {
          h.pld++; a.pld++;
          h.gf += m.home.goals; h.ga += m.away.goals;
          a.gf += m.away.goals; a.ga += m.home.goals;
          if (m.home.goals > m.away.goals)      { h.w++; h.pts += 3; a.l++; }
          else if (m.home.goals < m.away.goals) { a.w++; a.pts += 3; h.l++; }
          else                                  { h.d++; a.d++; h.pts++; a.pts++; }
        }
        i++;
      }
      var snap = orderTable(JSON.parse(JSON.stringify(rows)));
      var pos = {};
      snap.forEach(function (r) { pos[r.team] = r.pos; });
      var t = totalsFor(pos);
      dates.push(day);
      top3.push(snap.slice(0, 3).map(function (r) { return SHORT[r.team]; }).join(", "));
      NAMES.forEach(function (n) { series[n].push(t[n]); });
    }
    return { dates: dates, series: series, top3: top3 };
  }

  function renderRace(hist) {
    history = hist;
    var box = document.getElementById("race");
    clear(box);
    if (!hist) {
      box.appendChild(el("div", "pending",
        "The race chart needs a few matchdays in the book. Check back once the season is under way."));
      return;
    }
    var W = 1000, H = 320, L = 42, R = 16, T = 14, B = 26;
    var iw = W - L - R, ih = H - T - B;
    var all = [];
    NAMES.forEach(function (n) { all = all.concat(hist.series[n]); });
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
    var padv = Math.max(4, Math.round((hi - lo) * 0.1));
    lo = Math.max(0, lo - padv); hi = hi + padv;
    var N = hist.dates.length;
    function X(i) { return L + (N === 1 ? iw / 2 : (i / (N - 1)) * iw); }
    function Y(v) { return T + ((v - lo) / (hi - lo)) * ih; }

    var wrap = el("div", "chartwrap");
    var s = svgEl("svg", { viewBox: "0 0 " + W + " " + H, role: "img",
      "aria-label": "Each player's running score across the season" });
    var cLine = tok("--line"), cDim = tok("--dim"), cInk = tok("--ink");

    for (var k = 0; k <= 4; k++) {
      var v = Math.round(lo + ((hi - lo) * k) / 4), y = Y(v);
      s.appendChild(svgEl("line", { x1: L, y1: y, x2: W - R, y2: y, stroke: cLine, "stroke-width": 1 }));
      var lb = svgEl("text", { x: L - 7, y: y + 4, fill: cDim, "font-size": 11, "text-anchor": "end",
        "font-family": "monospace" });
      lb.textContent = v;
      s.appendChild(lb);
    }
    var seen = null;
    hist.dates.forEach(function (d, i) {
      var mo = d.slice(0, 7);
      if (mo === seen) return;
      seen = mo;
      var x = X(i);
      s.appendChild(svgEl("line", { x1: x, y1: T, x2: x, y2: T + ih, stroke: cLine, "stroke-width": 1, opacity: .55 }));
      var lb2 = svgEl("text", { x: x, y: H - 9, fill: cDim, "font-size": 11, "text-anchor": "middle",
        "font-family": "monospace" });
      lb2.textContent = MONS[Number(d.slice(5, 7)) - 1];
      s.appendChild(lb2);
    });

    var guide = svgEl("line", { x1: 0, y1: T, x2: 0, y2: T + ih, stroke: cInk, "stroke-width": 1, opacity: 0 });
    s.appendChild(guide);

    var dots = [];
    NAMES.forEach(function (n, idx) {
      var col = playerColor(idx);
      var pts = hist.series[n].map(function (v, i) { return X(i).toFixed(1) + "," + Y(v).toFixed(1); }).join(" ");
      s.appendChild(svgEl("polyline", { points: pts, fill: "none", stroke: col,
        "stroke-width": 2, "stroke-linejoin": "round" }));
      s.appendChild(svgEl("circle", { cx: X(N - 1), cy: Y(hist.series[n][N - 1]), r: 3, fill: col }));
      var d = svgEl("circle", { cx: 0, cy: 0, r: 3.6, fill: col, stroke: cInk, "stroke-width": 1, opacity: 0 });
      s.appendChild(d);
      dots.push(d);
    });

    wrap.appendChild(s);
    var tip = el("div", "tip");
    wrap.appendChild(tip);
    box.appendChild(wrap);

    function at(clientX) {
      var r = s.getBoundingClientRect();
      var rel = ((clientX - r.left) / r.width) * W;
      return Math.max(0, Math.min(N - 1, Math.round(((rel - L) / iw) * (N - 1))));
    }
    function show(ev) {
      var i = at(ev.clientX);
      guide.setAttribute("x1", X(i)); guide.setAttribute("x2", X(i));
      guide.setAttribute("opacity", .45);
      var ranked = NAMES.map(function (n, idx) {
        return { n: n, v: hist.series[n][i], c: playerColor(idx) };
      }).sort(function (a, b) { return a.v - b.v; });
      NAMES.forEach(function (n, idx) {
        dots[idx].setAttribute("cx", X(i));
        dots[idx].setAttribute("cy", Y(hist.series[n][i]));
        dots[idx].setAttribute("opacity", 1);
      });
      clear(tip);
      var dt = new Date(hist.dates[i] + "T12:00:00Z");
      tip.appendChild(el("div", "td",
        DAYS[dt.getUTCDay()] + " " + dt.getUTCDate() + " " + MONS[dt.getUTCMonth()] +
        "  ·  matchday " + (i + 1) + "/" + N));
      ranked.forEach(function (x, pos) {
        var r = el("div", "tr" + (pos === 0 ? " hi" : ""));
        var sw = el("i"); sw.style.background = x.c;
        r.appendChild(sw);
        r.appendChild(el("span", null, x.n));
        r.appendChild(el("b", null, x.v));
        tip.appendChild(r);
      });
      if (hist.top3[i]) {
        var t3 = el("div", "td", "TOP 3: " + hist.top3[i]);
        t3.style.margin = "6px 0 0";
        tip.appendChild(t3);
      }
      tip.style.display = "block";
      var wr = wrap.getBoundingClientRect();
      var px = ev.clientX - wr.left + 14;
      if (px + tip.offsetWidth > wr.width - 8) px = ev.clientX - wr.left - tip.offsetWidth - 14;
      tip.style.left = Math.max(8, px) + "px";
      tip.style.top = Math.max(8, Math.min(wr.height - tip.offsetHeight - 8, ev.clientY - wr.top - 10)) + "px";
    }
    function hide() {
      tip.style.display = "none";
      guide.setAttribute("opacity", 0);
      dots.forEach(function (d) { d.setAttribute("opacity", 0); });
    }
    s.addEventListener("pointermove", show);
    s.addEventListener("pointerdown", show);
    s.addEventListener("pointerleave", hide);

    var leg = el("div", "racelegend");
    NAMES.map(function (n, idx) { return { n: n, v: hist.series[n][N - 1], c: playerColor(idx) }; })
         .sort(function (a, b) { return a.v - b.v; })
         .forEach(function (x) {
      var sp = el("span");
      var sw = el("i"); sw.style.background = x.c;
      sp.appendChild(sw);
      sp.appendChild(document.createTextNode(x.n + " "));
      sp.appendChild(el("b", null, x.v));
      leg.appendChild(sp);
    });
    wrap.appendChild(leg);
  }

  /* ---------- odds ---------- */
  function pois(lam) {
    var Lx = Math.exp(-lam), k = 0, p = 1;
    do { k++; p *= Math.random(); } while (p > Lx);
    return k - 1;
  }
  var oddsCache = null;
  function renderOdds() {
    if (!oddsCache) return;
    var box = document.getElementById("odds");
    clear(box);
    var wrap = el("div", "odds");
    oddsCache.forEach(function (x) {
      var col = playerColor(NAMES.indexOf(x.n));
      var row = el("div", "orow");
      var nm = el("span", "on", x.n);
      nm.style.color = col;
      row.appendChild(nm);
      var tr = el("span", "track"), fl = el("span", "fill");
      fl.style.width = Math.max(x.p > 0 ? 1.5 : 0, x.p) + "%";
      fl.style.background = col;
      tr.appendChild(fl); row.appendChild(tr);
      var pc = el("span", "pc", x.p < 1 && x.p > 0 ? "<1%" : Math.round(x.p) + "%");
      pc.style.color = col;
      row.appendChild(pc);
      wrap.appendChild(row);
    });
    box.appendChild(wrap);
  }
  function runOdds(list, fixtures) {
    var box = document.getElementById("odds");
    var remaining = fixtures.filter(function (m) { return m.state === "pre"; });
    var played = list.reduce(function (s, r) { return s + r.pld; }, 0);
    if (played < 20) {
      clear(box);
      box.appendChild(el("div", "pending",
        "Odds need a few matchdays of form to work from. Check back once the season is under way."));
      return;
    }
    if (!remaining.length) {
      clear(box);
      box.appendChild(el("div", "pending", "Season complete — the table above is final."));
      return;
    }
    var avg = list.reduce(function (s, r) { return s + r.gf; }, 0) / Math.max(1, played);
    var base = {};
    list.forEach(function (r) {
      base[r.team] = {
        atk: r.pld ? (r.gf / r.pld) / avg : 1,
        def: r.pld ? (r.ga / r.pld) / avg : 1
      };
    });
    var wins = {};
    NAMES.forEach(function (n) { wins[n] = 0; });
    var done = 0;
    function batch() {
      var end = Math.min(done + 100, SIMS);
      for (; done < end; done++) {
        var st = {};
        list.forEach(function (r) { st[r.team] = { team: r.team, pts: r.pts, gf: r.gf, ga: r.ga }; });
        remaining.forEach(function (m) {
          var H = base[m.home.name], A = base[m.away.name];
          if (!H || !A) return;
          var hg = pois(Math.min(4, Math.max(0.15, avg * H.atk * A.def * 1.15)));
          var ag = pois(Math.min(4, Math.max(0.15, avg * A.atk * H.def * 0.88)));
          var h = st[m.home.name], a = st[m.away.name];
          h.gf += hg; h.ga += ag; a.gf += ag; a.ga += hg;
          if (hg > ag) h.pts += 3; else if (ag > hg) a.pts += 3; else { h.pts++; a.pts++; }
        });
        var fin = Object.keys(st).map(function (k) { return st[k]; });
        fin.sort(function (x, y) {
          return y.pts - x.pts || (y.gf - y.ga) - (x.gf - x.ga) || y.gf - x.gf || x.team.localeCompare(y.team);
        });
        var pos = {};
        fin.forEach(function (r, i) { pos[r.team] = i + 1; });
        var t = totalsFor(pos), best = Infinity, champs = [];
        NAMES.forEach(function (n) {
          if (t[n] < best) { best = t[n]; champs = [n]; }
          else if (t[n] === best) champs.push(n);
        });
        champs.forEach(function (n) { wins[n] += 1 / champs.length; });
      }
      if (done < SIMS) { setTimeout(batch, 0); return; }
      oddsCache = NAMES.map(function (n) { return { n: n, p: (wins[n] / SIMS) * 100 }; })
                       .sort(function (a, b) { return b.p - a.p; });
      renderOdds();
      document.getElementById("oddshint").textContent =
        SIMS.toLocaleString() + " simulated seasons · a rough model, not a crystal ball";
    }
    batch();
  }

  /* ---------- notices ---------- */
  function renderOffline() {
    var box = document.getElementById("notice");
    clear(box);
    var n = el("div", "note");
    n.appendChild(el("b", null, "CAN'T REACH THE SCOREBOARD. "));
    n.appendChild(document.createTextNode(
      "The live table is unavailable right now — it retries on its own. Everyone's picks are below in the meantime."));
    box.appendChild(n);
    ["sectable","secgrid","secmatches","secrace","secodds","secdamage","sech2h"].forEach(function (id) {
      document.getElementById(id).hidden = true;
    });
    renderBoard(null, false);
    renderPot(null);
  }
  function renderNotice(started) {
    var box = document.getElementById("notice");
    clear(box);
    ["sectable","secgrid","secrace","secodds"].forEach(function (id) {
      document.getElementById(id).hidden = false;
    });
    if (started) return;
    var n = el("div", "note");
    n.appendChild(el("b", null, "NOT A BALL KICKED YET. "));
    n.appendChild(document.createTextNode(
      "Scores stay dark until the first whistle — an empty table is just alphabetical order, " +
      "and nobody deserves to lead on that. Open a name to see their picks."));
    box.appendChild(n);
  }
  function setStatus(text, bad) {
    var s = document.getElementById("stat");
    s.className = bad ? "err" : "";
    s.textContent = text;
  }

  /* ---------- fun facts: a handful drawn fresh on every page load ---------- */
  function factPot() {
    return MONEY.players + " players, $" + MONEY.buyIn + " each — a $" + MONEY.pot +
           " pot, with $" + MONEY.prizes[0] + " going to whoever tops the table.";
  }
  function factTitleConsensus() {
    var tally = {};
    NAMES.forEach(function (n) {
      CLUBS.forEach(function (c) { if (PRED[n][c] === 1) tally[c] = (tally[c] || 0) + 1; });
    });
    var best = null;
    Object.keys(tally).forEach(function (c) { if (!best || tally[c] > tally[best]) best = c; });
    if (!best) return null;
    return tally[best] + " of " + NAMES.length + " picked <b>" + SHORT[best] + "</b> to win it all.";
  }
  function factBottomConsensus() {
    var tally = {};
    NAMES.forEach(function (n) {
      CLUBS.forEach(function (c) { if (PRED[n][c] === 20) tally[c] = (tally[c] || 0) + 1; });
    });
    var best = null;
    Object.keys(tally).forEach(function (c) { if (!best || tally[c] > tally[best]) best = c; });
    if (!best) return null;
    return tally[best] + " of " + NAMES.length + " picked <b>" + SHORT[best] + "</b> to finish bottom.";
  }
  function factWidestSpread() {
    var best = null, bestSpread = -1, hi = null, lo = null;
    CLUBS.forEach(function (c) {
      var preds = NAMES.map(function (n) { return { n: n, v: PRED[n][c] }; });
      var h = preds.reduce(function (a, b) { return b.v > a.v ? b : a; });
      var l = preds.reduce(function (a, b) { return b.v < a.v ? b : a; });
      if (h.v - l.v > bestSpread) { bestSpread = h.v - l.v; best = c; hi = h; lo = l; }
    });
    if (!best || bestSpread === 0) return null;
    return "Biggest disagreement: <b>" + SHORT[best] + "</b> — " + lo.n + " has them " +
           ordinal(lo.v) + ", " + hi.n + " has them " + ordinal(hi.v) + ".";
  }
  function factUnanimous() {
    var found = null;
    CLUBS.some(function (c) {
      var vals = NAMES.map(function (n) { return PRED[n][c]; });
      if (vals.every(function (v) { return v === vals[0]; })) { found = { c: c, v: vals[0] }; return true; }
      return false;
    });
    if (!found) return null;
    return "Total agreement: everyone predicted <b>" + SHORT[found.c] + "</b> to finish " + ordinal(found.v) + ".";
  }
  function factBoldestCall() {
    var best = null, bestDev = -1;
    CLUBS.forEach(function (c) {
      var vals = NAMES.map(function (n) { return PRED[n][c]; });
      NAMES.forEach(function (n, i) {
        var others = vals.filter(function (_, j) { return j !== i; });
        var avg = others.reduce(function (a, b) { return a + b; }, 0) / others.length;
        var dev = Math.abs(vals[i] - avg);
        if (dev > bestDev) { bestDev = dev; best = { n: n, c: c, v: vals[i], avg: avg }; }
      });
    });
    if (!best || bestDev < 3) return null;
    return "Boldest single pick: <b>" + best.n + "</b> has <b>" + SHORT[best.c] + "</b> at " +
           ordinal(best.v) + ", while everyone else averages " + best.avg.toFixed(1) + ".";
  }
  function factLeader(scored) {
    if (!scored || !scored.length) return null;
    return "<b>" + scored[0].name + "</b> currently leads the group on a score of " +
           scored[0].total + " — lower is better.";
  }
  function factRaceGap(scored) {
    if (!scored || scored.length < 2) return null;
    var tied = scored.filter(function (p) { return p.total === scored[0].total; });
    if (tied.length > 1) return "It's a dead heat at the top: " +
      tied.map(function (p) { return p.name; }).join(" and ") + " share the lead.";
    var gap = scored[1].total - scored[0].total;
    return "Just " + gap + " point" + (gap === 1 ? "" : "s") + " separate" + (gap === 1 ? "s" : "") +
           " 1st and 2nd place right now.";
  }
  function factExactLeader(scored) {
    if (!scored || !scored.length) return null;
    var best = scored[0];
    scored.forEach(function (p) { if (p.exact > best.exact) best = p; });
    if (best.exact === 0) return null;
    return "<b>" + best.name + "</b> has nailed " + best.exact + " club" +
           (best.exact === 1 ? "" : "s") + " exactly right so far.";
  }
  function factMatchweek(list) {
    var mw = list.reduce(function (m, r) { return Math.max(m, r.pld); }, 0);
    if (mw < 1) return null;
    return "Matchweek " + mw + " — the real table already looks different from the pre-season picture.";
  }
  function factPainClub(list) {
    var best = null, bestPain = -1;
    list.forEach(function (r) {
      var pain = 0;
      NAMES.forEach(function (n) { pain += Math.abs(PRED[n][r.team] - r.pos); });
      if (pain > bestPain) { bestPain = pain; best = r; }
    });
    if (!best) return null;
    return "<b>" + SHORT[best.team] + "</b>, currently " + ordinal(best.pos) +
           ", is causing the most collective pain — " + bestPain + " places of error across the group.";
  }

  function renderFacts(started, list, scored) {
    var pool = [factPot, factTitleConsensus, factBottomConsensus, factWidestSpread,
                factUnanimous, factBoldestCall];
    var facts = pool.map(function (fn) { return fn(); });
    if (started && list && scored) {
      facts = facts.concat([
        factLeader(scored), factRaceGap(scored), factExactLeader(scored),
        factMatchweek(list), factPainClub(list)
      ]);
    }
    facts = facts.filter(Boolean);
    for (var i = facts.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = facts[i]; facts[i] = facts[j]; facts[j] = tmp;
    }
    var ul = document.getElementById("factslist");
    clear(ul);
    facts.slice(0, 3).forEach(function (f) {
      var li = document.createElement("li");
      li.innerHTML = f;
      ul.appendChild(li);
    });
  }

  /* ---------- fetching ---------- */
  function windowDates() {
    function f(d) { return d.getUTCFullYear() + pad(d.getUTCMonth() + 1) + pad(d.getUTCDate()); }
    var now = Date.now();
    return f(new Date(now - 3 * 864e5)) + "-" + f(new Date(now + 4 * 864e5));
  }
  function grab(url) {
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }
  function loadSeason(list) {
    if (seasonTried) return;
    seasonTried = true;
    grab(SEASON).then(function (j) {
      seasonFixtures = parseMatches(j);
      renderRace(buildHistory(seasonFixtures));
      runOdds(list, seasonFixtures);
    }).catch(function () {
      var r = document.getElementById("race");
      clear(r); r.appendChild(el("div", "pending", "Couldn't load the season history."));
      var o = document.getElementById("odds");
      clear(o); o.appendChild(el("div", "pending", "Couldn't load the fixtures needed to simulate."));
    });
  }

  /* A shared link opens that person's card and scrolls down to it. */
  function resolveDeepLink() {
    var m = /[?&]p=([^&]+)/.exec(location.search);
    if (!m) return;
    var want = decodeURIComponent(m[1].replace(/\+/g, " ")).toLowerCase().trim();
    var hit = NAMES.concat(PENDING).filter(function (n) { return n.toLowerCase() === want; })[0];
    if (!hit) return;
    wantPlayer = hit;
    if (NAMES.indexOf(hit) !== -1) openCards[hit] = true;   // set BEFORE the first render
  }

  function scrollToPlayer(name) {
    var row = document.querySelector('.brow[data-player="' + name + '"]');
    if (!row) return false;
    var mid = Math.max(0, row.getBoundingClientRect().top + window.pageYOffset
              - (window.innerHeight / 2) + (row.offsetHeight / 2));
    var before = window.pageYOffset;
    if (reduceMotion) {
      window.scrollTo(0, mid);
    } else {
      try { window.scrollTo({ top: mid, behavior: "smooth" }); }
      catch (e) { window.scrollTo(0, mid); }
      /* smooth scrolling is a no-op in some contexts (hidden tab, older engines),
         so make sure we actually ended up there */
      setTimeout(function () {
        if (Math.abs(window.pageYOffset - before) < 4 && Math.abs(mid - before) > 20) {
          window.scrollTo(0, mid);
        }
      }, 450);
    }
    row.classList.add("flash");
    setTimeout(function () { row.classList.remove("flash"); }, 3400);
    return true;
  }

  /* ---------- poll loop ---------- */
  function cycle() {
    setStatus("REFRESHING…");
    Promise.all([grab(STANDINGS), grab(SCORES + windowDates())])
      .then(function (res) {
        var rows = parseStandings(res[0]);
        var matches = parseMatches(res[1]);
        var scorer = null;
        matches.forEach(function (m) {
          var key = m.home.goals + "-" + m.away.goals;
          if (m.state === "in" && lastScores[m.id] !== undefined && lastScores[m.id] !== key) {
            goalAt[m.id] = Date.now();
            scorer = m;
          }
          lastScores[m.id] = key;
        });

        applyLive(rows, matches);
        var list = orderTable(rows);
        currentList = list;
        var started = list.some(function (r) { return r.pld > 0; });
        var posByTeam = {};
        list.forEach(function (r) { posByTeam[r.team] = r.pos; });
        var totals = started ? totalsFor(posByTeam) : null;
        var scored = started ? scoreEveryone(posByTeam) : null;
        currentScored = scored;

        renderNotice(started);
        renderMatches(matches);
        renderBoard(scored, started);
        renderTable(list, started);
        renderGrid(list, started);
        renderDamage(list, started);
        renderH2H();
        if (started) applyH2HLink();
        renderPot(scored);

        if (!factsShown) { renderFacts(started, list, scored); factsShown = true; }

        if (scorer && totals) {
          renderGoalReport(scorer, totals, posByTeam, scored);
          celebrate(SHORT[scorer.home.name] + " " + scorer.home.goals + "-" +
                    scorer.away.goals + " " + SHORT[scorer.away.name] +
                    (scorer.clock ? "  " + scorer.clock : ""));
        }

        if (wantPlayer) {
          var target = wantPlayer;
          wantPlayer = null;
          setTimeout(function () { scrollToPlayer(target); }, 90);
        }

        hasData = true;
        prevTotals = totals;
        prevPos = posByTeam;
        prevLeader = scored && scored.length ? scored[0].name : null;

        loadSeason(list);

        var live = matches.filter(function (m) { return m.state === "in"; }).length;
        var t = new Date();
        setStatus((live ? "LIVE · " + live + " IN PLAY · " : "") +
                  "UPDATED " + pad(t.getHours()) + ":" + pad(t.getMinutes()) + ":" + pad(t.getSeconds()));
        schedule(live > 0);
      })
      .catch(function (err) {
        if (!hasData) renderOffline();
        if (!factsShown) { renderFacts(false, null, null); factsShown = true; }
        setStatus("SIGNAL LOST — " + err.message + " · RETRYING", true);
        /* A failure here — dropped request, ESPN hiccup, anything thrown
           above — always retries soon. Reusing the long idle interval once
           hasData was already true left the page silently stuck for up to
           10 minutes on any transient error, which looked like it needed a
           manual refresh to "wake up". */
        clearTimeout(timer);
        timer = setTimeout(cycle, 20000);
      });
  }
  function schedule(live) {
    clearTimeout(timer);
    timer = setTimeout(cycle, live ? LIVE_MS : (hasData ? IDLE_MS : 20000));
  }
  document.addEventListener("visibilitychange", function () { if (!document.hidden) cycle(); });

  applyTheme(savedTheme);
  resolveDeepLink();
  resolveH2HLink();
  initH2H();
  renderPot(null);
  cycle();

  /* a little welcome flash: the same off-register slip hover gives you, held
     for a beat right after the page loads */
  var mastLink = document.querySelector(".mast h1 a");
  if (mastLink && !reduceMotion) {
    setTimeout(function () {
      mastLink.classList.add("slip");
      setTimeout(function () { mastLink.classList.remove("slip"); }, 2000);
    }, 500);
  }
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    build()
