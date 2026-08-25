"""Two visual skins over identical structure. Each defines the same token set
three times: bare :root (its home ground), an auto flip for the other
preference, and both [data-theme] stamps so the toggle wins either way."""

# ------------------------------------------------------------------ teletext
TELETEXT_FONTS = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=JetBrains+Mono:wght@400;500;600;700&'
    'family=Martian+Mono:wght@600;700;800&display=swap">'
)

_TT_DARK = """
  --bg: #000000; --panel: #080c10; --band: #0e141a; --hover: #151d25;
  --ink: #f2f5f7; --dim: #8d9aa5; --line: #232e38; --line2: #303d48;
  --ylw: #ffd400; --cyn: #35dcf4; --grn: #46e88c; --mag: #ff6ecb;
  --red: #ff5a4d; --org: #ffa94d; --vio: #ad8dff; --blu: #4a6cff;
  --h1: var(--ylw); --h1b: var(--ylw); --h1glow: 0 0 26px rgba(255,212,0,.20);
  --chipink: #000000; --scan: rgba(255,255,255,.026); --shadow: none;
  --p1:#35dcf4; --p2:#46e88c; --p3:#ffd400; --p4:#ff6ecb; --p5:#ff5a4d;
  --p6:#f2f5f7; --p7:#ffa94d; --p8:#ad8dff; --p9:#7de3c0; --p10:#ffb3d8; --p11:#9fb4c4;
"""

_TT_LIGHT = """
  --bg: #eceef1; --panel: #ffffff; --band: #f4f6f8; --hover: #e7ebef;
  --ink: #0c1216; --dim: #55636d; --line: #d2d9df; --line2: #bcc6ce;
  --ylw: #8a6200; --cyn: #06697f; --grn: #0b6b36; --mag: #a5136f;
  --red: #b32414; --org: #94500a; --vio: #503bb5; --blu: #1b3fc4;
  --h1: #0c1216; --h1b: #0c1216; --h1glow: none;
  --chipink: #ffffff; --scan: transparent;
  --shadow: 0 1px 2px rgba(12,18,22,.06), 0 6px 18px rgba(12,18,22,.05);
  --p1:#06697f; --p2:#0b6b36; --p3:#8a6200; --p4:#a5136f; --p5:#b32414;
  --p6:#2b3a45; --p7:#94500a; --p8:#503bb5; --p9:#0f7c66; --p10:#b0447e; --p11:#657581;
"""

_TT_TYPE = """
  --mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  --disp: "Martian Mono", "JetBrains Mono", ui-monospace, monospace;
  --body: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  --h1w: 800; --h1ls: -.045em; --h1tt: none;
"""

TELETEXT_CSS = f""":root {{{_TT_TYPE}{_TT_DARK}}}
@media (prefers-color-scheme: light) {{ :root:not([data-theme="dark"]) {{{_TT_LIGHT}}} }}
:root[data-theme="light"] {{{_TT_LIGHT}}}
:root[data-theme="dark"] {{{_TT_DARK}}}

/* teletext keeps the block-character bars */
.brow .bar b {{ display: inline; }}
.brow .bar i {{ display: none; }}
"""

# ----------------------------------------------------------------- programme
PROGRAMME_FONTS = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=Anton&'
    'family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&'
    'family=Barlow+Condensed:wght@500;600;700&display=swap">'
)

_PR_LIGHT = """
  --bg: #e7e4dc; --panel: #f3f1ea; --band: #ebe8e0; --hover: #e0dcd1;
  --ink: #14161a; --dim: #5d5f66; --line: #14161a26; --line2: #14161a4d;
  --ylw: #a86a00; --cyn: #1b3f8f; --grn: #14663a; --mag: #97205f;
  --red: #c0281f; --org: #b0530b; --vio: #4b3a99; --blu: #1b3f8f;
  --h1: #14161a; --h1b: #1b3f8f; --h1glow: none;
  --chipink: #f3f1ea; --scan: transparent;
  --shadow: 0 1px 0 rgba(20,22,26,.10);
  --p1:#1b3f8f; --p2:#14663a; --p3:#a86a00; --p4:#97205f; --p5:#c0281f;
  --p6:#2c3138; --p7:#b0530b; --p8:#4b3a99; --p9:#0f6b5e; --p10:#a84a76; --p11:#6b7280;
"""

_PR_DARK = """
  --bg: #14161a; --panel: #1b1e24; --band: #20242b; --hover: #272c34;
  --ink: #ece8de; --dim: #9c9689; --line: #ece8de24; --line2: #ece8de40;
  --ylw: #e6a338; --cyn: #7d9de8; --grn: #58c98c; --mag: #e478ad;
  --red: #ef6a5c; --org: #e08a45; --vio: #a596ea; --blu: #7d9de8;
  --h1: #ece8de; --h1b: #e6a338; --h1glow: none;
  --chipink: #14161a; --scan: transparent;
  --shadow: none;
  --p1:#7d9de8; --p2:#58c98c; --p3:#e6a338; --p4:#e478ad; --p5:#ef6a5c;
  --p6:#ece8de; --p7:#e08a45; --p8:#a596ea; --p9:#6fd3bd; --p10:#eea3c6; --p11:#a8b4c0;
"""

_PR_TYPE = """
  --mono: "Barlow Condensed", "Helvetica Neue", sans-serif;
  --disp: "Anton", Impact, "Haettenschweiler", sans-serif;
  --body: "Source Serif 4", Georgia, "Times New Roman", serif;
  --h1w: 400; --h1ls: -.015em; --h1tt: uppercase;
"""

PROGRAMME_CSS = f""":root {{{_PR_TYPE}{_PR_LIGHT}}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{{_PR_DARK}}} }}
:root[data-theme="dark"] {{{_PR_DARK}}}
:root[data-theme="light"] {{{_PR_LIGHT}}}

/* newsprint tooth */
body {{
  background-image: radial-gradient(rgba(20,22,26,.055) 1px, transparent 1px);
  background-size: 4px 4px;
}}
:root[data-theme="dark"] body,
:root:not([data-theme="light"]) body {{ background-image: none; }}
@media (prefers-color-scheme: light) {{
  :root:not([data-theme="dark"]) body {{
    background-image: radial-gradient(rgba(20,22,26,.055) 1px, transparent 1px);
    background-size: 4px 4px;
  }}
}}

/* Anton is a display face — never for running text */
.mast .tag {{ font-size: 17px; line-height: 1.55; }}
h2 {{ letter-spacing: .14em; }}

/* programme swaps the block bars for a printed rule */
.brow .bar b {{ display: none; }}
.brow .bar i {{ display: block; }}
.brow .bar {{ color: var(--red); }}
.brow.lead .bar {{ color: var(--grn); }}

/* Dark crests (Spurs, Newcastle, Fulham...) vanish on a dark ground, so in the
   night edition every badge sits on its own small light plate — the way a
   printed programme prints them on white paper. */
.badgeplate {{
  background: #f4f2ec; border-radius: 2px; padding: 1.5px;
  box-shadow: 0 0 0 1px rgba(20,22,26,.10);
}}

/* dotted leaders, like a programme's contents page */
.brmain {{ grid-template-columns: 30px 172px 1fr 74px 92px; }}
.brow .nm {{ font-size: 21px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.brow .pos {{
  background: var(--blu); color: var(--chipink);
  width: 26px; height: 26px; display: grid; place-items: center;
  font-family: var(--disp); font-size: 14px;
}}
.brow.lead .pos {{ background: var(--red); color: var(--chipink); }}
.brow .tot {{ font-size: 25px; }}
.potcell .v, .h2hscore .num, .orow .pc {{ letter-spacing: 0; }}
@media (max-width: 700px) {{
  .brmain {{ grid-template-columns: 26px 1fr 62px 84px; }}
}}
"""

# The teletext skin is retired but kept above — put it back in SKINS to revive it.
SKINS = {
    "programme": {
        "fonts": PROGRAMME_FONTS,
        "css": PROGRAMME_CSS,
        "out": "index.html",
        "badges": True,
        "title": "The Nogosek Premiership &middot; 2026-27",
        "mast": "<span>Nogosek</span><em>Premiership</em>",
    },
}
