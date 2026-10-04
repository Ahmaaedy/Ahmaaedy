#!/usr/bin/env python3
"""Generate self-hosted SVG stat cards for a GitHub profile README.

Live mode  (needs GH_TOKEN with read:user, and GH_USER):
    python scripts/generate.py
Preview with fake data, no network:
    python scripts/generate.py --demo --out preview
Add --static to drop all animation (handy for rasterising a preview).

Writes stats.svg, streak.svg, langs.svg and year.svg into the output dir.
Output contains no timestamps, so a daily run only commits when data changes.
"""
import argparse
import datetime as dt
import os
import random
from html import escape
from dotenv import load_dotenv
load_dotenv()

# Rosé Pine palette, a staple of the ricing scene.
C = {
    "base": "#191724",
    "overlay": "#26233a",
    "muted": "#6e6a86",
    "text": "#e0def4",
    "pine": "#31748f",
    "foam": "#9ccfd8",
    "iris": "#c4a7e7",
    "love": "#eb6f92",
    "gold": "#f6c177",
}
FONT = "'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace"
FS = 13
CHAR_W = 0.6 * FS  # monospace advance, used only to park the cursor

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoriesWithContributedCommits
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      nodes {
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


# ---------------------------------------------------------------- data ----
def fetch(login, token):
    import requests

    r = requests.post(
        "https://api.github.com/graphql",
        json={"query": QUERY, "variables": {"login": login}},
        headers={"Authorization": f"bearer {token}"},
        timeout=30,
    )
    r.raise_for_status()
    payload = r.json()
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]["user"]


def demo_data():
    rng = random.Random(7)
    today = dt.date.today()
    start = today - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)  # back to a Sunday
    weeks, day, total = [], start, 0
    while day <= today:
        week = []
        for _ in range(7):
            if day <= today:
                n = rng.choice([0, 0, 0, 1, 2, 3, 5, 8, 12]) if rng.random() > 0.25 else 0
                total += n
                week.append({"date": day.isoformat(), "contributionCount": n})
            day += dt.timedelta(days=1)
        weeks.append({"contributionDays": week})
    langs = [("Python", 520000, "#3572A5"), ("JavaScript", 310000, "#f1e05a"),
             ("TypeScript", 190000, "#3178c6"), ("CSS", 90000, "#563d7c"),
             ("HTML", 60000, "#e34c26"), ("Rust", 22000, "#dea584")]
    return {
        "followers": {"totalCount": 12},
        "contributionsCollection": {
            "totalCommitContributions": 640,
            "totalPullRequestContributions": 18,
            "totalIssueContributions": 6,
            "totalRepositoriesWithContributedCommits": 14,
            "contributionCalendar": {"totalContributions": total, "weeks": weeks},
        },
        "repositories": {"nodes": [{"languages": {"edges": [
            {"size": s, "node": {"name": n, "color": c}} for n, s, c in langs]}}]},
    }


def flatten(user):
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = []
    for w in cal["weeks"]:
        for d in w["contributionDays"]:
            days.append((dt.date.fromisoformat(d["date"]), d["contributionCount"]))
    return days


def streaks(days):
    counts = [c for _, c in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    i = len(counts) - 1
    if i >= 0 and counts[i] == 0:  # today isn't over yet
        i -= 1
    current = 0
    while i >= 0 and counts[i] > 0:
        current += 1
        i -= 1
    return current, longest


def language_totals(user):
    totals, colors = {}, {}
    for repo in user["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            totals[name] = totals.get(name, 0) + e["size"]
            colors[name] = e["node"]["color"] or C["iris"]
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:6]
    grand = sum(totals.values()) or 1
    return [(n, b / grand * 100, colors[n]) for n, b in ranked]


# ----------------------------------------------------------------- svg ----
def card(login, w, h, prompt, body, animate):
    ps = f"{login}@arch ~ $ {prompt}"
    cx = 20 + CHAR_W * len(ps) + 4
    cursor = ""
    if animate:
        cursor = (f'<rect x="{cx:.1f}" y="19" width="{CHAR_W:.1f}" height="14" fill="{C["foam"]}">'
                  '<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" '
                  'dur="1.1s" repeatCount="indefinite"/></rect>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{escape(prompt)}">\n'
        f'<rect width="{w}" height="{h}" rx="8" fill="{C["base"]}"/>\n'
        f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="7.5" fill="none" stroke="{C["overlay"]}"/>\n'
        f'<g font-family="{FONT}" font-size="{FS}">\n'
        f'<text x="20" y="30" fill="{C["muted"]}">{escape(login)}@arch '
        f'<tspan fill="{C["foam"]}">~</tspan> $ <tspan fill="{C["text"]}">{escape(prompt)}</tspan></text>\n'
        f'{cursor}\n{body}\n</g>\n</svg>\n'
    )


def row(y, key, value, w, value_fill=None):
    return (f'<text x="20" y="{y}" fill="{C["muted"]}">{escape(key)}</text>'
            f'<text x="{w-20}" y="{y}" fill="{value_fill or C["text"]}" text-anchor="end">{escape(str(value))}</text>')


def bar(x, y, width, fill, animate, h=8):
    anim = ""
    if animate and width > 0:
        anim = (f'<animate attributeName="width" from="0" to="{width:.1f}" dur="0.9s" '
                'begin="0s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.2 0.8 0.2 1"/>')
    return (f'<rect x="{x}" y="{y-h+1}" width="{width:.1f}" height="{h}" rx="2" fill="{fill}">{anim}</rect>')


def stats_svg(login, user, animate):
    cc = user["contributionsCollection"]
    rows = [
        ("contributions, past year", cc["contributionCalendar"]["totalContributions"], C["foam"]),
        ("commits", cc["totalCommitContributions"], None),
        ("pull requests", cc["totalPullRequestContributions"], None),
        ("issues", cc["totalIssueContributions"], None),
        ("repos committed to", cc["totalRepositoriesWithContributedCommits"], None),
        ("followers", user["followers"]["totalCount"], None),
    ]
    w, h = 495, 62 + 24 * len(rows) - 6
    body = "".join(row(62 + 24 * i, k, f"{v:,}" if isinstance(v, int) else v, w, f)
                   for i, (k, v, f) in enumerate(rows))
    return card(login, w, h, "stats --year", body, animate)


def streak_svg(login, days, animate):
    cur, longest = streaks(days)
    active = sum(1 for _, c in days if c > 0)
    top = max(longest, 1)
    items = [("current", cur, f"{cur} days", C["foam"], cur / top),
             ("longest", longest, f"{longest} days", C["iris"], 1.0),
             ("active days", active, f"{active} of {len(days)}", C["gold"], active / max(len(days), 1))]
    w, h = 495, 62 + 28 * len(items) - 10
    body = ""
    for i, (k, _, label, fill, ratio) in enumerate(items):
        y = 62 + 28 * i
        body += (f'<text x="20" y="{y}" fill="{C["muted"]}">{k}</text>'
                 f'<rect x="140" y="{y-7}" width="220" height="8" rx="2" fill="{C["overlay"]}"/>'
                 + bar(140, y, 220 * ratio, fill, animate)
                 + f'<text x="{w-20}" y="{y}" fill="{C["text"]}" text-anchor="end">{escape(label)}</text>')
    return card(login, w, h, "streak", body, animate)


def langs_svg(login, langs, animate):
    w, h = 495, 62 + 26 * max(len(langs), 1) - 8
    body = ""
    top = langs[0][1] if langs else 1
    for i, (name, pct, color) in enumerate(langs):
        y = 62 + 26 * i
        body += (f'<text x="20" y="{y}" fill="{C["text"]}">{escape(name)}</text>'
                 f'<rect x="140" y="{y-7}" width="260" height="8" rx="2" fill="{C["overlay"]}"/>'
                 + bar(140, y, 260 * pct / top, color, animate)
                 + f'<text x="{w-20}" y="{y}" fill="{C["muted"]}" text-anchor="end">{pct:.1f}%</text>')
    if not langs:
        body = f'<text x="20" y="62" fill="{C["muted"]}">no public repos yet</text>'
    return card(login, w, h, "langs --public", body, animate)


RAMP = [(".", C["muted"]), (":", C["pine"]), ("+", C["foam"]), ("#", C["iris"]), ("@", C["love"])]


def year_svg(login, days, animate):
    nonzero = sorted(c for _, c in days if c > 0)

    def level(c):
        if c == 0 or not nonzero:
            return 0
        q = lambda p: nonzero[min(len(nonzero) - 1, int(len(nonzero) * p))]
        return 1 + (c > q(0.25)) + (c > q(0.5)) + (c > q(0.75))

    cols = {}
    first = days[0][0] - dt.timedelta(days=(days[0][0].weekday() + 1) % 7)
    for d, c in days:
        col = (d - first).days // 7
        r = (d.weekday() + 1) % 7  # Sunday on top
        cols.setdefault(col, {})[r] = c
    ncols = max(cols) + 1
    cw, rh = 10, 14
    w, h = 40 + ncols * cw, 54 + 7 * rh + 34
    body = ""
    for col in range(ncols):
        cells = ""
        for r, c in sorted(cols.get(col, {}).items()):
            ch, fill = RAMP[level(c)]
            cells += (f'<text x="{20 + col*cw + cw/2:.1f}" y="{58 + r*rh}" fill="{fill}" '
                      f'text-anchor="middle">{ch}</text>')
        if animate:
            body += (f'<g opacity="0">{cells}<animate attributeName="opacity" from="0" to="1" '
                     f'dur="0.25s" begin="{col*0.03:.2f}s" fill="freeze"/></g>')
        else:
            body += f"<g>{cells}</g>"
    ly = 58 + 7 * rh + 14
    legend = f'<text x="20" y="{ly}" fill="{C["muted"]}">quiet</text>'
    for i, (ch, fill) in enumerate(RAMP):
        legend += f'<text x="{68 + i*14}" y="{ly}" fill="{fill}" text-anchor="middle">{ch}</text>'
    legend += f'<text x="{68 + len(RAMP)*14 - 4}" y="{ly}" fill="{C["muted"]}">loud</text>'
    return card(login, w, h, "year", body + legend, animate)


# ---------------------------------------------------------------- main ----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="use fake data, no network")
    ap.add_argument("--static", action="store_true", help="omit animation")
    ap.add_argument("--out", default=os.environ.get("OUT_DIR", "."))
    args = ap.parse_args()

    login = os.environ.get("GH_USER", "your-username")
    if args.demo:
        user = demo_data()
    else:
        token = os.environ.get("GH_TOKEN")
        if not token:
            raise SystemExit("Set GH_TOKEN (a token with read:user) or use --demo.")
        user = fetch(login, token)

    animate = not args.static
    days = flatten(user)
    files = {
        "stats.svg": stats_svg(login, user, animate),
        "streak.svg": streak_svg(login, days, animate),
        "langs.svg": langs_svg(login, language_totals(user), animate),
        "year.svg": year_svg(login, days, animate),
    }
    os.makedirs(args.out, exist_ok=True)
    for name, svg in files.items():
        with open(os.path.join(args.out, name), "w", encoding="utf-8") as f:
            f.write(svg)
        print("wrote", os.path.join(args.out, name))


if __name__ == "__main__":
    main()
