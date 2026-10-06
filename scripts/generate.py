#!/usr/bin/env python3
"""Generate self-hosted, monochrome SVG graphics for a GitHub profile README.

Live mode  (needs GH_TOKEN with read:user, and GH_USER):
    python scripts/generate.py
Preview with fake data, no network:
    python scripts/generate.py --demo --out preview
Add --static to drop all animation (handy for rasterising a preview).

Writes stats.svg, streak.svg, langs.svg, year.svg and five hd-*.svg section
headings into the output dir. Output has no timestamps, so a daily run only
commits when the data changes.
"""
import argparse
import datetime as dt
import os
import random
from html import escape

# Black and white, one muted grey between. #0d1117 is GitHub's dark canvas, so
# the graphics melt into the page in dark mode.
C = {
    "bg": "#0d1117",
    "text": "#f0f6fc",
    "muted": "#8b949e",
    "dim": "#484f58",
    "light": "#c9d1d9",
    "rule": "#21262d",
    "area": "#1c2128",
}
FONT = "'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace"
W = 620
PAD = 20

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      nodes {
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
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
                n = rng.choice([0, 0, 1, 2, 3, 5, 8, 12, 30]) if rng.random() > 0.55 else 0
                total += n
                week.append({"date": day.isoformat(), "contributionCount": n})
            day += dt.timedelta(days=1)
        weeks.append({"contributionDays": week})
    repo_langs = [
        [("TypeScript", 190000), ("CSS", 40000)],
        [("Python", 300000), ("JavaScript", 20000)],
        [("Python", 220000)],
        [("MDX", 160000), ("TypeScript", 90000)],
        [("Rust", 22000), ("Python", 12000)],
        [("Liquid", 9000), ("JavaScript", 14000)],
    ]
    return {
        "followers": {"totalCount": 12},
        "contributionsCollection": {"contributionCalendar": {"totalContributions": total, "weeks": weeks}},
        "repositories": {"nodes": [
            {"languages": {"edges": [{"size": s, "node": {"name": n}} for n, s in langs]}}
            for langs in repo_langs]},
    }


def flatten(user):
    cal = user["contributionsCollection"]["contributionCalendar"]
    return [(dt.date.fromisoformat(d["date"]), d["contributionCount"])
            for w in cal["weeks"] for d in w["contributionDays"]]


def weekly_totals(user):
    cal = user["contributionsCollection"]["contributionCalendar"]
    return [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]]


def streaks(days):
    """Return (current, current_range, longest, longest_range)."""
    best, best_range, run, start = 0, None, 0, None
    for d, c in days:
        if c > 0:
            if run == 0:
                start = d
            run += 1
            if run > best:
                best, best_range = run, (start, d)
        else:
            run = 0
    i = len(days) - 1
    if i >= 0 and days[i][1] == 0:  # today isn't over yet
        i -= 1
    end = days[i][0] if i >= 0 else None
    cur, cur_start = 0, None
    while i >= 0 and days[i][1] > 0:
        cur, cur_start = cur + 1, days[i][0]
        i -= 1
    return cur, ((cur_start, end) if cur else None), best, best_range


def language_stats(user):
    totals, repos = {}, {}
    for repo in user["repositories"]["nodes"]:
        seen = set()
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            totals[name] = totals.get(name, 0) + e["size"]
            if name not in seen:
                repos[name] = repos.get(name, 0) + 1
                seen.add(name)
    grand = sum(totals.values()) or 1
    by_bytes = [(n, b / grand * 100) for n, b in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:5]]
    by_repos = sorted(repos.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    return by_bytes, by_repos


# ----------------------------------------------------------------- svg ----
def fmt_range(r):
    if not r:
        return "\u2014"
    a, b = r
    if a == b:
        return f"{a:%b} {a.day}".lower()
    return f"{a:%b} {a.day} \u2013 {b:%b} {b.day}".lower()


def svg(h, label, body, defs=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" '
        f'role="img" aria-label="{escape(label)}">\n{defs}'
        f'<rect width="{W}" height="{h}" fill="{C["bg"]}"/>\n'
        f'<g font-family="{FONT}" font-size="13" fill="{C["muted"]}">\n{body}\n</g>\n</svg>\n'
    )


def t(x, y, s, fill=None, size=None, anchor=None, weight=None, ls=None):
    a = f' x="{x}" y="{y}"'
    if fill:
        a += f' fill="{fill}"'
    if size:
        a += f' font-size="{size}"'
    if anchor:
        a += f' text-anchor="{anchor}"'
    if weight:
        a += f' font-weight="{weight}"'
    if ls:
        a += f' letter-spacing="{ls}"'
    return f"<text{a}>{escape(str(s))}</text>"


def short(name):
    n = name.lower()
    return n if len(n) <= 11 else n[:10] + "\u2026"


def label_caps(x, y, s):
    return t(x, y, s.upper(), fill=C["muted"], size=10, ls=2)


def bar(x, y, width, animate, h=6):
    anim = ""
    if animate and width > 0:
        anim = (f'<animate attributeName="width" from="0" to="{width:.1f}" dur="0.9s" begin="0s" '
                'fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.2 0.8 0.2 1"/>')
    return f'<rect x="{x}" y="{y}" width="{width:.1f}" height="{h}" rx="1" fill="{C["light"]}">{anim}</rect>'


def stats_svg(user, days, animate):
    cal = user["contributionsCollection"]["contributionCalendar"]
    weeks = weekly_totals(user)
    active = sum(1 for _, c in days if c > 0)
    best = max(weeks) if weeks else 0

    left, right = PAD, W - PAD
    top, base = 116, 190
    n = len(weeks)
    peak = max(max(weeks, default=0), 1)
    pts = [(left + i * (right - left) / max(n - 1, 1), base - w / peak * (base - top))
           for i, w in enumerate(weeks)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"M{left},{base} " + " ".join(f"L{x:.1f},{y:.1f}" for x, y in pts) + f" L{pts[-1][0]:.1f},{base} Z"
    ex, ey = pts[-1]

    reveal = ""
    if animate:
        reveal = (f'<animate attributeName="width" from="0" to="{right-left+8}" dur="1.2s" begin="0s" '
                  'fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.2 0.8 0.2 1"/>')
    defs = (f'<defs><clipPath id="reveal"><rect x="{left}" y="0" width="{right-left+8}" height="210">'
            f'{reveal}</rect></clipPath></defs>\n')

    body = (
        t(left, 66, f"{cal['totalContributions']:,}", fill=C["text"], size=56, weight=600)
        + t(left, 90, "contributions in the last year")
        + t(right, 38, active, fill=C["text"], size=22, anchor="end", weight=600)
        + t(right, 54, "active days", size=11, anchor="end")
        + t(right, 80, best, fill=C["text"], size=22, anchor="end", weight=600)
        + t(right, 96, "best week", size=11, anchor="end")
        + f'<g clip-path="url(#reveal)"><path d="{area}" fill="{C["area"]}"/>'
        f'<polyline points="{line}" fill="none" stroke="{C["light"]}" stroke-width="1.5" '
        'stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="3.5" fill="{C["text"]}"/></g>'
        f'<line x1="{left}" y1="{base}" x2="{right}" y2="{base}" stroke="{C["rule"]}"/>'
    )
    return svg(210, "Contributions in the last year", body, defs)


def streak_svg(days, animate):
    cur, cur_r, longest, long_r = streaks(days)
    mid = W // 2
    body = (
        t(PAD, 62, cur, fill=C["text"], size=56, weight=600)
        + t(PAD, 86, "current streak")
        + t(PAD, 106, fmt_range(cur_r), fill=C["dim"], size=12)
        + f'<line x1="{mid}" y1="26" x2="{mid}" y2="112" stroke="{C["rule"]}"/>'
        + t(mid + 24, 62, longest, fill=C["text"], size=56, weight=600)
        + t(mid + 24, 86, "longest streak")
        + t(mid + 24, 106, fmt_range(long_r), fill=C["dim"], size=12)
    )
    return svg(130, "Current and longest streak", body)


def langs_svg(user, animate):
    by_bytes, by_repos = language_stats(user)
    rows = max(len(by_bytes), len(by_repos), 1)
    h = 56 + 22 * rows + 12
    colw, barw = 280, 116
    left, right = PAD, W // 2 + 20
    body = label_caps(left, 28, "by bytes") + label_caps(right, 28, "by repos")
    top_b = by_bytes[0][1] if by_bytes else 1
    top_r = by_repos[0][1] if by_repos else 1
    for i, (name, pct) in enumerate(by_bytes):
        y = 56 + 22 * i
        body += (t(left, y, short(name), fill=C["text"], weight=600)
                 + bar(left + 96, y - 8, barw * pct / top_b, animate)
                 + t(left + colw - 20, y, f"{pct:.0f}%", anchor="end"))
    for i, (name, n) in enumerate(by_repos):
        y = 56 + 22 * i
        body += (t(right, y, short(name), fill=C["text"], weight=600)
                 + bar(right + 96, y - 8, barw * n / top_r, animate)
                 + t(W - PAD, y, n, anchor="end"))
    if not by_bytes:
        body += t(left, 56, "no public repos yet")
    return svg(h, "Top languages by bytes and by repos", body)


RAMP = [(":", C["dim"]), ("+", C["muted"]), ("#", C["light"]), ("@", C["text"])]


def year_svg(days, animate):
    nonzero = sorted(c for _, c in days if c > 0)

    def level(c):  # 0 = draw nothing, 1..4 = ramp index + 1
        if c == 0 or not nonzero:
            return 0
        q = lambda p: nonzero[min(len(nonzero) - 1, int(len(nonzero) * p))]
        return 1 + (c > q(0.25)) + (c > q(0.5)) + (c > q(0.75))

    first = days[0][0] - dt.timedelta(days=(days[0][0].weekday() + 1) % 7)
    cols = {}
    for d, c in days:
        cols.setdefault((d - first).days // 7, {})[(d.weekday() + 1) % 7] = (d, c)
    ncols = max(cols) + 1
    x0, rh, top = 52, 14, 82
    cw = (W - PAD - x0) / ncols
    active = sum(1 for _, c in days if c > 0)
    h = top + 7 * rh + 34

    body = (label_caps(PAD, 28, "the year")
            + t(PAD, 52, f"{active} of {len(days)} days had a contribution"))
    # legend, right-aligned: less : + # @ more
    body += t(499, 52, "less", size=11, anchor="end")
    for i, (ch, fill) in enumerate(RAMP):
        body += t(513 + i * 14, 52, ch, fill=fill, anchor="middle")
    body += t(569, 52, "more", size=11)
    for r, name in ((1, "mon"), (3, "wed"), (5, "fri")):
        body += t(PAD, top + r * rh, name, size=10)

    last_label_col, last_month = -9, None
    for col in range(ncols):
        cells = ""
        for r, (d, c) in sorted(cols.get(col, {}).items()):
            lv = level(c)
            if lv:
                ch, fill = RAMP[lv - 1]
                cells += t(f"{x0 + col * cw + cw / 2:.1f}", top + r * rh, ch, fill=fill, anchor="middle")
        if cells:
            if animate:
                body += (f'<g opacity="0">{cells}<animate attributeName="opacity" from="0" to="1" '
                         f'dur="0.25s" begin="{col * 0.03:.2f}s" fill="freeze"/></g>')
            else:
                body += f"<g>{cells}</g>"
        any_day = next(iter(cols.get(col, {}).values()), None)
        if any_day and any_day[0].month != last_month and col - last_label_col >= 3:
            body += t(f"{x0 + col * cw:.1f}", top + 7 * rh + 10, f"{any_day[0]:%b}".lower(), size=10)
            last_label_col = col
        if any_day:
            last_month = any_day[0].month
    return svg(h, "The last year, one character per day", body)


def heading_svg(text):
    body = (label_caps(PAD, 24, text)
            + f'<line x1="{PAD}" y1="34" x2="{W - PAD}" y2="34" stroke="{C["rule"]}"/>')
    return svg(44, text, body)


# ---------------------------------------------------------------- main ----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="use fake data, no network")
    ap.add_argument("--static", action="store_true", help="omit animation")
    ap.add_argument("--out", default=os.environ.get("OUT_DIR", "."))
    args = ap.parse_args()

    if args.demo:
        user = demo_data()
    else:
        login = os.environ.get("GH_USER", "")
        token = "".join((os.environ.get("GH_TOKEN") or "").split())
        if not login or not token:
            raise SystemExit("Set GH_USER and GH_TOKEN (a token with read:user), or use --demo.")
        user = fetch(login, token)

    animate = not args.static
    days = flatten(user)
    files = {
        "stats.svg": stats_svg(user, days, animate),
        "streak.svg": streak_svg(days, animate),
        "langs.svg": langs_svg(user, animate),
        "year.svg": year_svg(days, animate),
        "hd-about.svg": heading_svg("about"),
        "hd-stack.svg": heading_svg("stack"),
        "hd-projects.svg": heading_svg("projects"),
        "hd-stats.svg": heading_svg("stats"),
        "hd-about-this-page.svg": heading_svg("about this page"),
    }
    os.makedirs(args.out, exist_ok=True)
    for name, content in files.items():
        with open(os.path.join(args.out, name), "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", os.path.join(args.out, name))


if __name__ == "__main__":
    main()
