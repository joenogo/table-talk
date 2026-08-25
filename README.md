# THE NOGOSEK PREMIERSHIP

A public scoreboard for the eleven-way Premier League table prediction league.
`site/index.html` is the whole website — one file, no backend, no build step,
no account, no dependency on Claude or on your laptop being awake.

## How the live updating works

The page talks straight to ESPN's public JSON API from the visitor's browser.
That API sends `access-control-allow-origin: *`, so no proxy or API key is
needed — which is what makes a plain static file enough.

Two calls per refresh:

| | |
|---|---|
| League table | `site.api.espn.com/apis/v2/sports/soccer/eng.1/standings` |
| Fixtures & live scores | `site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard?dates=…` |

A third call fetches all 380 fixtures for the season, once, after the first
render — that one file carries every past result *and* every remaining fixture,
which is what powers the race chart and the odds.

Then, in the browser:

1. In-play matches are applied on top of the confirmed table, so the standings
   are **as it stands right now**, mid-match — not the last completed matchweek.
2. Everyone's score is recomputed: `|your slot − real slot|` summed over 20 clubs.
3. **Refreshes every 60 seconds whenever a match is in play**, every 10 minutes
   otherwise, and immediately whenever someone switches back to the tab.

Every visitor fetches independently, so it stays live for all of them at once.
If ESPN is unreachable the page keeps the last good table, says `SIGNAL LOST`,
and retries in 20 seconds — always, regardless of whether it had already loaded
successfully once. (An earlier version reused the long idle interval for this,
so a single transient failure after the first successful load could leave the
page quietly stuck for up to 10 minutes — looking exactly like "needs a
refresh". Fixed: any failure now retries quickly.) On a cold start with no
connection it still shows everyone's picks rather than an empty screen.

## What's on the page

| Section | What it does |
|---|---|
| **The Pot** | $25 x 11 = $275, paying $125 / $90 / $60, with the current holder of each place. |
| **Vidiprinter** | Live scores with the clock. A goal flashes the score yellow, tags it `GOAL` and tints the row. |
| **Goal report** | After every goal: which clubs changed position, every player's new score and delta, and whether the lead changed hands. Dismissable. |
| **The Reckoning** | The leaderboard, with prize money on the top three. Click a name for all 20 picks, exact hits, average gap and worst call. Each row has a **LINK** button that copies a direct URL to that person's card. |
| **The Season Race** | Every player's running score across the season, rebuilt from past results — one point per matchday. Hover (or tap) anywhere on the chart for that matchday's full standings and the top three clubs at the time. |
| **Title Odds** | 2,000 simulated seasons, run in the browser, giving each person a live chance of winning. A Poisson model off goals scored and conceded, with home advantage — a rough model, and labelled as one. |
| **As It Stands** | The real table. `●` marks a club currently playing. |
| **Who Backed Whom** | Every prediction with each club's current position, coloured by how far out it is, with a legend. Rows are ordered by where each club actually sits in the table, not alphabetically. |
| **Damage Report** | The clubs causing the most collective pain, and who each one is hurting worst. |
| **Head to Head** | Both totals side by side with ranks, the gap, a bar showing who is closer on how many clubs, and the ten clubs where you most disagree. *Same gap* counts the clubs where you are both exactly as far out. **COPY LINK** copies a URL (`?h2h=NameA,NameB`) that opens straight into that exact pairing. |
| **Did You Know** | Three facts drawn at random on every page load, from a pool built off the predictions (biggest disagreement, boldest single pick, title/relegation consensus) plus, once the season is under way, the live table (current leader, exact hits, the gap for 1st vs 2nd, which club is causing the most collective pain). Sits in the header, beside the masthead. |

Sections that would be meaningless before the season starts hide themselves
until there's data.

**Theme** — light / dark / auto, in the header, remembered per browser. Auto
follows the device. Dark is the design's home ground; light is a
printed-results-page treatment of the same layout.

**Masthead** — clicking the title returns to the top of the page (`href="."`,
which also drops any `?p=` query string). Hovering it, or ~0.5s after the page
loads, the two words slide apart with an off-register colour ghost, like a
printing plate slipping — same effect either way, the load just fires it once
automatically so it isn't only ever discovered by accident.

**Section order** is: the reckoning, fixtures, the season race, as it stands,
head to head, who backed whom, damage report, title odds, the pot.

## The look

Matchday programme: Anton + Source Serif on newsprint, numbered rank squares,
printed rule bars, and every club's badge. Light / dark / auto toggle in the
header — light is home, dark is a designed night edition rather than an
inversion.

Styling lives in `_skins.py` as a skin block that is appended **after** the
shared CSS so its overrides win — order matters there. The retired teletext
skin is still in that file; re-register it in `SKINS` to build it again.

## Goal effects

When a goal lands, a banner wipes across the middle of the page: `GOAL!` set
large, the fixture and minute under it, and a ball flying into a net on the
right. It clears itself after about eight seconds, or right away if you click
anywhere outside it. Clicking the banner itself does nothing. FX are **on** by default and
remembered per browser.

| Sound | Source |
|---|---|
| Kick | synthesised (WebAudio) |
| Net | synthesised (WebAudio) |
| Crowd | `audio/crowd.m4a` — Millerntor stadium reaction, trimmed to its loudest 5.4s and compressed to 36 KB |

The crowd sample is decoded once into an audio buffer at load and played through
WebAudio, so playback never stalls, never rejects, and overlapping goals layer
instead of cutting each other off. It is embedded as a data URI, so the page
stays a single file — replace the file and re-run `make.py` to change it.

Browsers refuse to let a page make noise before the visitor has clicked
something. Rather than failing silently, if a goal lands before then the page
shows a small prompt — *"Click anywhere to turn the goal sounds on"* — which
disappears on the first click. Nothing is scheduled into a suspended audio
context, so no sounds queue up and fire late.

The banner is skipped entirely for anyone with *reduce motion* set, and while
the tab is in the background.

## Favicon

The Premier League lion, cropped out of the full logo lockup (the wordmark is
illegible at 16px). `art/crest96.png` is composited onto an opaque paper square
inside an SVG wrapper and inlined as a data URI, so it reads on a dark browser
tab as well as a light one. `art/crest180.png` is copied to `site/favicon.png`
at build time as a fallback and as the Apple touch icon — so if you upload only
`index.html`, the inline SVG still works on its own.

## Club names and badges

Two name sets live in `make.py`: `FULL` for roomy columns (the league table, the
damage report, who backed whom) and `SHORT` for the narrow ones (the pick
columns, head to head, the vidiprinter). Both are proper case and shortened
rather than nicknamed — no `SPURS`, no `C PALACE`.

In the night edition every badge sits on a small light plate, because dark
crests — Tottenham, Newcastle, Fulham — disappear against a dark ground. The
plates are added and removed as the theme changes.

## The money

`make.py` holds the buy-in, the roster and the payouts:

```python
PENDING = ["Joe", "Katie"]             # in the pot, not yet scoreable
BUY_IN  = 25
PRIZES  = [125, 90, 60]
```

The build **fails** if the prizes don't add up to `BUY_IN x players`, so the pot
can never silently disagree with itself. When Joe or Katie hand a table in, add
their column to the CSV, drop them from `PENDING`, and re-run `make.py`.

Ties are shown honestly rather than guessed at: two players level on first place
both show as 1st, and second place shows a dash. Decide how you want to split
the money in that case and tell me — right now the page states the fact and
leaves the maths to you.

## Putting it online

The site is one static file, so any static host works. Two good routes:

### Netlify (fastest — about two minutes)

1. Go to **app.netlify.com/drop** and drag the `site` folder onto the page.
   It's live immediately at some `random-name.netlify.app`.
2. Create the free account it offers, so the site sticks around.
3. **Site configuration → Domain management → Add a domain** → `pl.joenogosek.com`.
   Netlify shows you the CNAME target.

### GitHub Pages (durable, versioned)

1. New repo → upload `site/index.html` to the root.
2. **Settings → Pages** → deploy from `main` / root.
3. **Settings → Pages → Custom domain** → `pl.joenogosek.com`.

### DNS at Squarespace

Squarespace registers the domain, so the record goes there —
**Domains → joenogosek.com → DNS → DNS Settings → Add record**:

| Host | Type | Data |
|---|---|---|
| `pl` | CNAME | whatever the host gave you (e.g. `your-site.netlify.app`) |

Give it 10–30 minutes. Your Google Sites site on the apex `joenogosek.com`
is untouched — this only adds the `pl.` subdomain.

If you'd rather it appeared inside the Google Sites site, embed it there once
the subdomain is live: **Insert → Embed → By URL →** `https://pl.joenogosek.com`.

## Changing the picks

Predictions are baked into the page, so they can't drift mid-season. To change
them, edit `premier-league-predictions-2026-27.csv` and regenerate:

```bash
python3 make.py
```

Then re-upload `site/index.html`. The script refuses to build if anyone's
column isn't exactly the 20 clubs in the league, so a typo fails loudly
instead of silently scoring someone wrong.

## Seeing the live behaviour before the season has one

`demo.html` (project root, **not** part of the upload) is the same page fed a
fully simulated season — 24 rounds played out, round 25 half-finished with five
matches in play, and a goal going in every ~11 seconds. Every section including
the race chart and the odds is derived by the page's own code from those
results, so it exercises the real logic rather than a hand-fed table. Double-click it. It polls every 4s instead of 60s so you don't
have to wait around, and carries a red DEMO strip so it can't be mistaken for
real data. Regenerate with `python3 make_demo.py`.

## Preview locally

```bash
python3 -m http.server 8792 --directory site
```

Opening `site/index.html` by double-clicking also works — ESPN allows it.

## Worth checking during the first live match

The page assumes ESPN's standings endpoint does **not** already include
in-progress matches, and adds them itself. That's how it behaves in every check
so far, but the first Saturday with games on is the moment to glance at whether
a club that's currently playing shows the right played-count. If it's ever
double-counted it self-corrects at full time; the fix would be one line in
`applyLive()`.

## Files

| File | Role |
|---|---|
| `premier-league-predictions-2026-27.csv` | The eight sets of picks. The source of truth. |
| `make.py` | Injects the picks into the page. Only needed if picks change. |
| `site/index.html` | The website. This is the thing you upload. |
| `site/favicon.png` | Generated fallback icon. Upload alongside it if you can. |
| `audio/crowd.m4a` | Crowd sample, embedded at build time. |
| `badges/` | 20 club badges, embedded into the build. |
| `art/` | The Premier League lion, used for the favicon. |
| `_skins.py` | The two visual skins. |
| `make_mockups.py`, `mockups.html` | The three exploratory directions. Not part of the site. |
| `demo.html` | Simulated live matchday. Not uploaded. |
| `make_demo.py` | Builds the demo from the same template as the real page. |
