#!/usr/bin/env python3
"""
Generates mockups.html — three alternative visual directions for Table Talk,
all showing the same (simulated) matchweek-25 data so they can be compared
fairly rather than on whose numbers look nicer.

Club badges are embedded as data URIs from ./badges/, so the page is
self-contained and works offline.

    python3 make_mockups.py
"""

import base64
import json
import pathlib

HERE = pathlib.Path(__file__).parent
BADGES = HERE / "badges"
DATA = HERE / "mockup-data.json"
OUT = HERE / "mockups.html"


def badge_uris():
    if not BADGES.exists():
        raise SystemExit(f"missing {BADGES} — club badges are embedded from there")
    out = {}
    for p in sorted(BADGES.glob("*.png")):
        out[p.stem] = "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode("ascii")
    if len(out) != 20:
        raise SystemExit(f"expected 20 badges in {BADGES}, found {len(out)}")
    return out


def build():
    d = json.loads(DATA.read_text())
    b = badge_uris()
    table, board, pending = d["table"], d["board"], d["pending"]

    def img(slug, size, extra=""):
        return (f'<img src="{b[slug]}" alt="" width="{size}" height="{size}" '
                f'style="width:{size}px;height:{size}px;object-fit:contain;{extra}">')

    # ---------- A: PROGRAMME ----------
    a_board = "".join(
        f'<li class="a-row{" a-lead" if p["rank"] == 1 else ""}">'
        f'<span class="a-rk">{p["rank"]}</span>'
        f'<span class="a-nm">{p["name"]}</span>'
        f'<span class="a-dot"></span>'
        f'<span class="a-cash">{"$" + str(p["cash"]) if p["cash"] else ""}</span>'
        f'<span class="a-tot">{p["total"]}</span></li>'
        for p in board)
    a_pending = " · ".join(pending)
    a_table = "".join(
        f'<tr{" class=q" if t["pos"] <= 5 else (" class=r" if t["pos"] >= 18 else "")}>'
        f'<td class="a-pos">{t["pos"]}</td>'
        f'<td class="a-badge">{img(t["slug"], 24)}</td>'
        f'<td class="a-club">{t["club"]}</td>'
        f'<td>{t["pld"]}</td><td>{"+" if t["gd"] > 0 else ""}{t["gd"]}</td>'
        f'<td class="a-pts">{t["pts"]}</td></tr>'
        for t in table)

    # ---------- B: BROADCAST ----------
    b_board = "".join(
        f'<div class="b-row{" b-lead" if p["rank"] == 1 else ""}">'
        f'<span class="b-chip">{p["rank"]}</span>'
        f'<span class="b-nm">{p["name"]}</span>'
        f'<span class="b-bar"><i style="width:{min(100, (p["total"] - board[0]["total"]) * 4 + 3)}%"></i></span>'
        f'<span class="b-tot">{p["total"]}</span>'
        f'<span class="b-gap">{"LEADER" if p["rank"] == 1 else "+" + str(p["total"] - board[0]["total"])}</span>'
        f'</div>'
        for p in board)
    b_table = "".join(
        f'<div class="b-trow">'
        f'<span class="b-tpos">{t["pos"]}</span>{img(t["slug"], 22)}'
        f'<span class="b-tclub">{t["club"]}</span>'
        f'<span class="b-tpts">{t["pts"]}</span></div>'
        for t in table[:8])

    # ---------- C: FANZINE ----------
    c_board = "".join(
        f'<div class="c-row">'
        f'<span class="c-rk">{p["rank"]}.</span>'
        f'<span class="c-nm">{p["name"]}</span>'
        f'<span class="c-lead"></span>'
        f'<span class="c-tot">{p["total"]}</span>'
        f'{"<span class=c-cash>$" + str(p["cash"]) + "</span>" if p["cash"] else "<span class=c-cash></span>"}'
        f'</div>'
        for p in board)

    html = TEMPLATE
    for k, v in {
        "A_BOARD": a_board, "A_TABLE": a_table, "A_PENDING": a_pending,
        "B_BOARD": b_board, "B_TABLE": b_table,
        "C_BOARD": c_board,
        "LEADER": board[0]["name"].upper(),
        "LEADER_TOT": str(board[0]["total"]),
    }.items():
        html = html.replace("{{" + k + "}}", v)

    assert "{{" not in html, "unsubstituted placeholder remains"
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT}  ({len(html):,} bytes)  20 badges embedded")


TEMPLATE = r"""<meta charset="utf-8">
<title>Three Directions</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Anton&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=Saira+Condensed:wght@500;700;800&family=Barlow+Condensed:wght@400;500;600&family=Archivo+Black&family=Courier+Prime:ital,wght@0,400;0,700;1,400&display=swap">
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0; background: #16181b; color: #e9ecef;
    font-family: "Barlow Condensed", system-ui, sans-serif;
  }
  .shell { max-width: 1180px; margin: 0 auto; padding: 32px 18px 90px; }

  .intro { border-bottom: 1px solid #2c3138; padding-bottom: 22px; margin-bottom: 34px; }
  .intro h1 {
    font-family: "Archivo Black", system-ui, sans-serif;
    font-size: clamp(26px, 4.4vw, 42px); margin: 0; letter-spacing: -.02em;
  }
  .intro p { color: #9aa4ae; font-size: 16px; max-width: 68ch; margin: 12px 0 0; line-height: 1.55; }

  .label { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 16px; margin: 54px 0 14px; }
  .label .tag {
    font-family: "Archivo Black", sans-serif; font-size: 12px; letter-spacing: .12em;
    background: #e9ecef; color: #16181b; padding: 4px 10px;
  }
  .label .nm { font-family: "Archivo Black", sans-serif; font-size: 21px; letter-spacing: -.01em; }
  .label .why { color: #9aa4ae; font-size: 15px; flex: 1 1 320px; }
  .label .why b { color: #e9ecef; font-weight: 600; }

  .frame { border: 1px solid #2c3138; overflow: hidden; }

  /* ============ A — PROGRAMME ============ */
  .A {
    background: #e7e4dc; color: #14161a; padding: 34px 32px 38px;
    font-family: "Source Serif 4", Georgia, serif;
    background-image: radial-gradient(#00000010 1px, transparent 1px);
    background-size: 4px 4px;
  }
  .A .head { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; flex-wrap: wrap; }
  .A h2 {
    font-family: "Anton", Impact, sans-serif; font-weight: 400;
    font-size: clamp(46px, 8vw, 92px); line-height: .82; margin: 0;
    letter-spacing: -.015em; text-transform: uppercase; color: #14161a;
  }
  .A h2 em { font-style: normal; color: #1b3f8f; display: block; }
  .A .issue {
    font-family: "Anton", sans-serif; font-size: 13px; letter-spacing: .16em;
    background: #c0281f; color: #fff; padding: 5px 11px; text-transform: uppercase;
  }
  .A .rule { height: 4px; background: #14161a; margin: 20px 0 0; }
  .A .rule.thin { height: 1px; background: #14161a44; margin: 14px 0; }

  .A .cols { display: grid; grid-template-columns: 1.05fr 1fr; gap: 34px; margin-top: 24px; }
  @media (max-width: 820px) { .A .cols { grid-template-columns: 1fr; } }

  .A .kicker {
    font-family: "Anton", sans-serif; font-size: 14px; letter-spacing: .16em;
    text-transform: uppercase; color: #1b3f8f; margin-bottom: 10px;
  }
  .A ol { list-style: none; margin: 0; padding: 0; }
  .A .a-row { display: flex; align-items: baseline; gap: 10px; padding: 7px 0; border-bottom: 1px solid #14161a22; }
  .A .a-rk {
    font-family: "Anton", sans-serif; font-size: 15px; width: 26px; height: 26px;
    background: #1b3f8f; color: #fff; display: grid; place-items: center; flex: none;
  }
  .A .a-lead .a-rk { background: #c0281f; }
  .A .a-nm { font-weight: 600; font-size: 19px; }
  .A .a-dot { flex: 1 1 auto; border-bottom: 1px dotted #14161a55; height: .7em; }
  .A .a-cash { font-family: "Anton", sans-serif; font-size: 14px; color: #c0281f; }
  .A .a-tot { font-family: "Anton", sans-serif; font-size: 23px; min-width: 44px; text-align: right; }
  .A .pend { font-size: 14px; font-style: italic; color: #14161a99; margin-top: 12px; }

  .A .pot { display: flex; gap: 0; border: 2px solid #14161a; margin-top: 18px; }
  .A .pot div { flex: 1; padding: 9px 12px; border-right: 1px solid #14161a33; }
  .A .pot div:last-child { border-right: 0; }
  .A .pot .k { font-family: "Anton", sans-serif; font-size: 10px; letter-spacing: .14em; color: #14161a88; }
  .A .pot .v { font-family: "Anton", sans-serif; font-size: 25px; }

  /* quirks mode does not inherit colour/font into tables, and this file ships
     without a doctype so an artifact host can supply one — so be explicit. */
  .A table {
    width: 100%; border-collapse: collapse; font-size: 15px;
    color: #14161a; font-family: "Source Serif 4", Georgia, serif;
  }
  .A th { display: none; }
  .A td { padding: 3px 5px; text-align: right; }
  .A .a-pos { font-family: "Anton", sans-serif; color: #14161a88; width: 26px; text-align: left; font-size: 13px; }
  .A .a-badge { width: 30px; text-align: center; }
  .A .a-club { text-align: left; width: 100%; font-weight: 600; }
  .A .a-pts { font-family: "Anton", sans-serif; font-size: 17px; }
  .A tr.q .a-pos { color: #1b3f8f; }
  .A tr.r .a-pos { color: #c0281f; }
  .A tbody tr:nth-child(even) { background: #14161a08; }

  /* ============ B — BROADCAST ============ */
  .B {
    background: linear-gradient(160deg, #071231 0%, #04091c 58%, #01030a 100%);
    color: #fff; padding: 32px 30px 38px;
    font-family: "Barlow Condensed", sans-serif;
  }
  .B .bar { display: flex; align-items: center; gap: 14px; }
  .B .live {
    font-family: "Saira Condensed", sans-serif; font-weight: 800; font-style: italic;
    font-size: 13px; letter-spacing: .1em; background: #e3122b; color: #fff;
    padding: 4px 12px; transform: skewX(-12deg);
  }
  .B .live span { display: inline-block; transform: skewX(12deg); }
  .B .mw { font-size: 14px; letter-spacing: .22em; color: #7f93b8; }
  .B h2 {
    font-family: "Saira Condensed", sans-serif; font-weight: 800; font-style: italic;
    font-size: clamp(40px, 7.6vw, 82px); line-height: .9; margin: 14px 0 0;
    letter-spacing: -.02em; text-transform: uppercase;
  }
  .B h2 span { color: #ccff00; }
  .B .lede { color: #9fb2d4; font-size: 16px; margin: 10px 0 0; }
  .B .glow { height: 3px; background: linear-gradient(90deg, #ccff00, #ccff0000); margin: 20px 0 22px; }

  .B .cols { display: grid; grid-template-columns: 1.25fr 1fr; gap: 26px; }
  @media (max-width: 820px) { .B .cols { grid-template-columns: 1fr; } }
  .B .kicker {
    font-family: "Saira Condensed", sans-serif; font-weight: 700; font-size: 12px;
    letter-spacing: .18em; color: #ccff00; margin-bottom: 10px;
  }

  .B .b-row {
    display: grid; grid-template-columns: 34px 1fr 120px 54px 62px;
    align-items: center; gap: 12px;
    background: #ffffff09; border-left: 3px solid #ffffff1a;
    padding: 8px 12px; margin-bottom: 4px;
  }
  .B .b-lead { background: #ccff0014; border-left-color: #ccff00; }
  .B .b-chip {
    font-family: "Saira Condensed", sans-serif; font-weight: 800; font-style: italic;
    font-size: 15px; background: #ffffff1a; padding: 2px 0; text-align: center;
    transform: skewX(-12deg);
  }
  .B .b-lead .b-chip { background: #ccff00; color: #04091c; }
  .B .b-nm {
    font-family: "Saira Condensed", sans-serif; font-weight: 700; font-style: italic;
    font-size: 20px; text-transform: uppercase; letter-spacing: -.01em;
  }
  .B .b-bar { height: 6px; background: #ffffff14; display: block; }
  .B .b-bar i { display: block; height: 100%; background: linear-gradient(90deg, #ccff00, #7fbf00); }
  .B .b-tot {
    font-family: "Saira Condensed", sans-serif; font-weight: 800; font-size: 25px;
    text-align: right; font-style: italic;
  }
  .B .b-gap { font-size: 13px; letter-spacing: .1em; color: #7f93b8; text-align: right; }

  .B .b-trow {
    display: grid; grid-template-columns: 24px 22px 1fr 34px;
    align-items: center; gap: 10px; padding: 6px 10px;
    border-bottom: 1px solid #ffffff10; font-size: 16px;
  }
  .B .b-tpos { color: #7f93b8; font-size: 13px; }
  .B .b-tclub { text-transform: uppercase; letter-spacing: .03em; }
  .B .b-tpts { font-family: "Saira Condensed", sans-serif; font-weight: 800; color: #ccff00; text-align: right; }

  .B .pot { display: flex; gap: 8px; margin-top: 16px; flex-wrap: wrap; }
  .B .pot div { flex: 1 1 90px; background: #ffffff0d; padding: 8px 11px; border-top: 2px solid #ccff00; }
  .B .pot .k { font-size: 12px; letter-spacing: .16em; color: #7f93b8; }
  .B .pot .v { font-family: "Saira Condensed", sans-serif; font-weight: 800; font-size: 24px; font-style: italic; }

  /* ============ C — FANZINE ============ */
  .C {
    background: #efe9dc; color: #1a1714; padding: 36px 30px 42px;
    font-family: "Courier Prime", "Courier New", monospace;
    background-image:
      radial-gradient(#2b4bd826 1.2px, transparent 1.3px),
      radial-gradient(#e8443a1f 1.2px, transparent 1.3px);
    background-size: 7px 7px, 7px 7px;
    background-position: 0 0, 3px 3px;
  }
  .C .staple { display: flex; gap: 7px; margin-bottom: 20px; }
  .C .staple i { width: 26px; height: 7px; background: #1a171433; transform: rotate(-2deg); display: block; }
  .C .zh { position: relative; display: inline-block; transform: rotate(-1.4deg); }
  /* riso off-register: the red plate printed a hair off the blue one */
  .C h2 {
    font-family: "Archivo Black", sans-serif; font-size: clamp(38px, 7.4vw, 78px);
    line-height: .86; margin: 0; text-transform: uppercase; letter-spacing: -.03em;
    color: #2b4bd8; text-shadow: 4px 4px 0 #e8443a;
  }
  .C .sub {
    font-size: 15px; margin: 16px 0 0; max-width: 56ch; line-height: 1.6;
    border-left: 3px solid #e8443a; padding-left: 12px;
  }
  .C .tapewrap { margin: 24px 0 6px; }
  .C .tape {
    display: inline-block; background: #e8443a; color: #efe9dc;
    font-family: "Archivo Black", sans-serif; font-size: 13px; letter-spacing: .1em;
    padding: 5px 14px; transform: rotate(-1.2deg); text-transform: uppercase;
  }
  .C .sheet {
    background: #f7f3ea; border: 2px solid #1a1714; padding: 16px 18px;
    box-shadow: 5px 5px 0 #2b4bd8; transform: rotate(.35deg);
  }
  .C .c-row {
    display: grid; grid-template-columns: 30px 1fr auto 56px 52px;
    gap: 9px; align-items: baseline; padding: 6px 0; border-bottom: 1px dashed #1a171444;
  }
  .C .c-row:last-child { border-bottom: 0; }
  .C .c-rk { font-weight: 700; color: #e8443a; }
  .C .c-nm { font-weight: 700; font-size: 17px; text-transform: uppercase; letter-spacing: -.02em; }
  .C .c-lead { border-bottom: 1px dotted #1a171455; height: .7em; }
  .C .c-tot {
    font-family: "Archivo Black", sans-serif; font-size: 20px; text-align: right; color: #2b4bd8;
  }
  .C .c-cash { font-weight: 700; color: #e8443a; text-align: right; font-size: 14px; }
  .C .foot { display: flex; flex-wrap: wrap; gap: 10px 26px; margin-top: 22px; font-size: 14px; }
  .C .foot b { background: #2b4bd8; color: #efe9dc; padding: 2px 8px; font-family: "Archivo Black", sans-serif; font-size: 13px; }
  .C .scrawl { font-size: 14px; margin-top: 18px; transform: rotate(-.6deg); color: #1a1714cc; }
</style>

<div class="shell">

  <div class="intro">
    <h1>Three directions for Table Talk</h1>
    <p>Same matchweek, same numbers, same eleven names — only the treatment changes,
       so you're judging the look and not the data. Teletext stays on the table as the
       fourth option; this is what else it could be.</p>
  </div>

  <!-- ============ A ============ -->
  <div class="label">
    <span class="tag">A</span>
    <span class="nm">Matchday Programme</span>
    <span class="why"><b>Every club's badge, in print.</b> Reads like something you'd buy
      outside the ground. Warmest and most collectable of the three — but the heaviest
      to scan on a phone mid-match.</span>
  </div>
  <div class="frame">
    <div class="A">
      <div class="head">
        <h2>Table<em>Talk</em></h2>
        <span class="issue">Matchweek 25</span>
      </div>
      <div class="rule"></div>
      <div class="cols">
        <div>
          <div class="kicker">The Reckoning</div>
          <ol>{{A_BOARD}}</ol>
          <div class="pend">Still to submit: {{A_PENDING}}</div>
          <div class="pot">
            <div><div class="k">Pot</div><div class="v">$275</div></div>
            <div><div class="k">First</div><div class="v">$125</div></div>
            <div><div class="k">Second</div><div class="v">$90</div></div>
            <div><div class="k">Third</div><div class="v">$60</div></div>
          </div>
        </div>
        <div>
          <div class="kicker">As It Stands</div>
          <table><tbody>{{A_TABLE}}</tbody></table>
        </div>
      </div>
    </div>
  </div>

  <!-- ============ B ============ -->
  <div class="label">
    <span class="tag">B</span>
    <span class="nm">Broadcast Graphics</span>
    <span class="why"><b>Saturday afternoon on the telly.</b> Skewed chips, lime on navy,
      italic condensed caps. Best sense of live occasion — but the style does the shouting,
      so quiet weeks look overdressed.</span>
  </div>
  <div class="frame">
    <div class="B">
      <div class="bar">
        <span class="live"><span>● LIVE</span></span>
        <span class="mw">MATCHWEEK 25 · 5 IN PLAY</span>
      </div>
      <h2>Table <span>Talk</span></h2>
      <p class="lede">{{LEADER}} leads on {{LEADER_TOT}} with thirteen rounds to play.</p>
      <div class="glow"></div>
      <div class="cols">
        <div>
          <div class="kicker">STANDINGS</div>
          {{B_BOARD}}
          <div class="pot">
            <div><div class="k">POT</div><div class="v">$275</div></div>
            <div><div class="k">1ST</div><div class="v">$125</div></div>
            <div><div class="k">2ND</div><div class="v">$90</div></div>
            <div><div class="k">3RD</div><div class="v">$60</div></div>
          </div>
        </div>
        <div>
          <div class="kicker">TOP OF THE TABLE</div>
          {{B_TABLE}}
        </div>
      </div>
    </div>
  </div>

  <!-- ============ C ============ -->
  <div class="label">
    <span class="tag">C</span>
    <span class="nm">Terrace Fanzine</span>
    <span class="why"><b>Photocopied and stapled.</b> Two spot colours off-register on
      newsprint, typewriter body, everything slightly crooked. By far the most personality
      — and the least serious, which is either the point or the problem.</span>
  </div>
  <div class="frame">
    <div class="C">
      <div class="staple"><i></i><i></i></div>
      <div class="zh"><h2>Table Talk</h2></div>
      <p class="sub">Eleven of us. Twenty-five dollars each. One league table doing its
         level best to embarrass the lot of you. Issue 25.</p>
      <div class="tapewrap"><span class="tape">The Damage So Far</span></div>
      <div class="sheet">{{C_BOARD}}</div>
      <div class="foot">
        <span><b>POT</b> $275</span>
        <span><b>1ST</b> $125</span>
        <span><b>2ND</b> $90</span>
        <span><b>3RD</b> $60</span>
      </div>
      <p class="scrawl">Joe, Rachel and Katie still haven't handed anything in.
         Money's in the pot, mind.</p>
    </div>
  </div>

</div>
"""


if __name__ == "__main__":
    build()
