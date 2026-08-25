#!/usr/bin/env python3
"""
Generates demo.html — the same page as docs/index.html, but fed a fabricated
season instead of ESPN.

Simulates a full 38-round fixture list, plays out the first 24 rounds, and
leaves round 25 half-finished with five matches in play. Everything the page
shows — the table, the race chart, the odds, the damage report — is derived by
the page's own code from those results, so this exercises the real logic end to
end rather than hand-feeding it a table.

Goals then go in every few seconds so the flash and the vidiprinter are
watchable without waiting for a real matchday.

    python3 make_demo.py
"""

import json
import pathlib
import random

from _skins import SKINS
from make import (ESPN_IDS, FULL, PENDING, SHORT, TEMPLATE, badge_uris,
                  crowd_data_uri, favicon_uri, load_predictions, money_config)

HERE = pathlib.Path(__file__).parent


NAME_TO_ID = {v: k for k, v in ESPN_IDS.items()}

# Rough pecking order used to generate results. Deliberately chaotic — Villa
# flying, United in crisis — so the pick grid has plenty to say.
QUALITY_ORDER = [
    "Aston Villa", "Arsenal", "Chelsea", "Sunderland", "Liverpool", "Brighton",
    "Manchester City", "Crystal Palace", "Brentford", "Newcastle", "Everton",
    "Bournemouth", "Fulham", "Coventry", "Nottingham Forest", "Tottenham",
    "Leeds", "Manchester United", "Ipswich", "Hull City",
]

ROUNDS_PLAYED = 24
LIVE_ROUND = 25
SEED = 2027


def round_robin(teams):
    """Circle method: 19 rounds of 10, then the same again with venues flipped."""
    ts = list(teams)
    n = len(ts)
    first = []
    fixed, rot = ts[0], ts[1:]
    for r in range(n - 1):
        pairs = [(fixed, rot[0])] if r % 2 == 0 else [(rot[0], fixed)]
        for i in range(1, n // 2):
            a, b = rot[i], rot[-i]
            pairs.append((a, b) if (r + i) % 2 == 0 else (b, a))
        first.append(pairs)
        rot = rot[1:] + rot[:1]
    second = [[(b, a) for a, b in rnd] for rnd in first]
    return first + second


def build_season():
    rng = random.Random(SEED)
    q = {t: 1.40 - (0.68 * i / 19) for i, t in enumerate(QUALITY_ORDER)}
    schedule = round_robin(QUALITY_ORDER)

    def goals(home, away):
        lh = min(4.2, max(0.25, 1.45 * (q[home] / q[away]) ** 0.9))
        la = min(4.2, max(0.25, 1.12 * (q[away] / q[home]) ** 0.9))
        return rng.poisson(lh) if hasattr(rng, "poisson") else poisson(rng, lh), \
               rng.poisson(la) if hasattr(rng, "poisson") else poisson(rng, la)

    fixtures = []
    for r, pairs in enumerate(schedule, start=1):
        day = 20 + (r - 1) * 7          # days after 2026-08-01
        for j, (h, a) in enumerate(pairs):
            f = {
                "id": f"{r:02d}{j:02d}",
                "home": NAME_TO_ID[h], "away": NAME_TO_ID[a],
                "round": r, "day": day,
                "hg": 0, "ag": 0, "state": "pre", "minute": 0,
            }
            if r <= ROUNDS_PLAYED:
                hg, ag = goals(h, a)
                f.update(hg=hg, ag=ag, state="post")
            elif r == LIVE_ROUND and j < 5:
                hg, ag = goals(h, a)
                f.update(hg=max(0, hg - 1), ag=max(0, ag - 1),
                         state="in", minute=rng.randint(28, 74))
            fixtures.append(f)
    return fixtures


def poisson(rng, lam):
    import math
    lim, k, p = math.exp(-lam), 0, 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= lim:
            return k - 1


def standings_from(fixtures):
    """Confirmed results only — the page folds the in-play games in itself."""
    rows = {tid: {"id": tid, "pld": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}
            for tid in ESPN_IDS}
    for f in fixtures:
        if f["state"] != "post":
            continue
        h, a = rows[f["home"]], rows[f["away"]]
        h["pld"] += 1; a["pld"] += 1
        h["gf"] += f["hg"]; h["ga"] += f["ag"]
        a["gf"] += f["ag"]; a["ga"] += f["hg"]
        if f["hg"] > f["ag"]:   h["w"] += 1; h["pts"] += 3; a["l"] += 1
        elif f["hg"] < f["ag"]: a["w"] += 1; a["pts"] += 3; h["l"] += 1
        else:                   h["d"] += 1; a["d"] += 1; h["pts"] += 1; a["pts"] += 1
    return list(rows.values())


def build():
    load_predictions()   # fail loudly if the CSV and the league disagree
    fixtures = build_season()
    table = standings_from(fixtures)

    ranked = sorted(table, key=lambda r: (-r["pts"], -(r["gf"] - r["ga"]), -r["gf"]))
    print(f"  simulated {ROUNDS_PLAYED} rounds — table after them:")
    for i, r in enumerate(ranked[:5], 1):
        print(f"    {i}. {ESPN_IDS[r['id']]:<18} {r['pts']:>2} pts")
    print(f"    ...  20. {ESPN_IDS[ranked[-1]['id']]} {ranked[-1]['pts']} pts")

    state = {"table": table, "fixtures": fixtures}
    stub = STUB.replace("__STATE__", json.dumps(state, separators=(",", ":")))

    players, preds = load_predictions()
    badges = badge_uris()
    common = {
        "__PREDICTIONS__": json.dumps(preds, separators=(",", ":"), sort_keys=True),
        "__TEAMS__": json.dumps(ESPN_IDS, separators=(",", ":"), sort_keys=True),
        "__SHORT__": json.dumps(SHORT, separators=(",", ":"), sort_keys=True),
        "__FULL__": json.dumps(FULL, separators=(",", ":"), sort_keys=True),
        "__PENDING__": json.dumps(PENDING, separators=(",", ":")),
        "__MONEY__": json.dumps(money_config(players), separators=(",", ":")),
        "__CROWD__": crowd_data_uri(),
        "__FAVICON__": favicon_uri(),
    }

    for skin, cfg in SKINS.items():
        html = TEMPLATE
        for k, v in common.items():
            html = html.replace(k, v)
        html = (html
                .replace("__SKIN_CSS__", cfg["css"])
                .replace("__FONTS__", cfg["fonts"])
                .replace("__TITLE__", cfg["title"] + " &middot; DEMO")
                .replace("__MAST__", cfg["mast"])
                .replace("__BADGES__",
                         json.dumps(badges, separators=(",", ":"), sort_keys=True)
                         if cfg["badges"] else "{}"))

        left = [t for t in ("__PREDICTIONS__", "__SKIN_CSS__", "__BADGES__", "__FULL__",
                            "__SHORT__", "__TEAMS__", "__MONEY__", "__PENDING__",
                            "__CROWD__", "__MAST__", "__TITLE__", "__FONTS__",
                            "__FAVICON__") if t in html]
        if left:
            raise SystemExit(f"{skin}: unsubstituted {left}")

        # poll fast so a simulated goal shows up while you are looking at it
        html = html.replace("var LIVE_MS = 60000, IDLE_MS = 600000;",
                            "var LIVE_MS = 4000, IDLE_MS = 4000;")

        marker = '<script>\n(function () {\n  "use strict";'
        assert html.count(marker) == 1, skin
        html = html.replace(marker, stub + marker)
        anchor = '  <div class="strip">'
        assert html.count(anchor) == 1, skin
        html = html.replace(anchor, DEMO_BANNER + anchor)

        out = HERE / "demo.html"
        out.write_text(html, encoding="utf-8")
        print(f"  {skin:<10} -> {out.name:<24} {len(html):>9,} bytes")
    print("  round 25 · 5 matches in play · a goal roughly every 11s")


DEMO_BANNER = """  <div class="demobar">
    <span class="dtag">DEMO</span>
    <span>Simulated season, round 25 &middot; goals fire every few seconds so you can watch the flash &middot; nothing here is real</span>
  </div>
  <style>
    .demobar {
      display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
      background: #1a0d00; border-bottom: 1px solid #4a2a00;
      margin: 0 -14px; padding: 7px 14px;
      font-size: 11px; letter-spacing: .06em; color: #b98a3a;
    }
    .dtag { background: #ff4438; color: #000; font-weight: 700; padding: 2px 7px; }
  </style>
"""


STUB = r"""<script>
/* ---- demo harness: stands in for ESPN, and scores goals on a timer ---- */
(function () {
  var S = __STATE__;

  function iso(day) {
    return new Date(Date.UTC(2026, 7, 1 + day, 15, 0)).toISOString();
  }

  function standings() {
    return { children: [{ standings: { entries: S.table.map(function (r) {
      return { team: { id: r.id }, stats: [
        { name: "gamesPlayed", value: r.pld }, { name: "wins", value: r.w },
        { name: "ties", value: r.d }, { name: "losses", value: r.l },
        { name: "pointsFor", value: r.gf }, { name: "pointsAgainst", value: r.ga },
        { name: "points", value: r.pts }, { name: "pointDifferential", value: r.gf - r.ga }
      ] };
    }) } }] };
  }

  function scoreboard() {
    return { events: S.fixtures.map(function (f) {
      return {
        id: f.id, date: iso(f.day),
        status: {
          displayClock: f.state === "in" ? f.minute + "'" : "",
          type: { state: f.state, shortDetail: f.state === "in" ? f.minute + "'" : (f.state === "post" ? "FT" : "") }
        },
        competitions: [{ competitors: [
          { homeAway: "home", team: { id: f.home }, score: String(f.hg) },
          { homeAway: "away", team: { id: f.away }, score: String(f.ag) }
        ] }]
      };
    }) };
  }

  window.fetch = function (url) {
    var body = String(url).indexOf("standings") > -1 ? standings() : scoreboard();
    return Promise.resolve({ ok: true, status: 200,
      json: function () { return Promise.resolve(body); } });
  };

  function live() { return S.fixtures.filter(function (f) { return f.state === "in"; }); }

  setInterval(function () {
    live().forEach(function (f) {
      f.minute += 1;
      if (f.minute >= 90) { f.state = "post"; }
    });
  }, 2500);

  setInterval(function () {
    var l = live();
    if (!l.length) return;
    var f = l[Math.floor(Math.random() * l.length)];
    if (Math.random() < 0.5) f.hg += 1; else f.ag += 1;
  }, 11000);
})();
</script>
"""


if __name__ == "__main__":
    build()
