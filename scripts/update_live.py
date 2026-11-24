#!/usr/bin/env python3
"""Refresh the live section of the profile README.

Public data only:
- streak and contribution counts come from the contribution calendar
  (numbers only, never repo names);
- "currently working on" and merged PRs come from public events and
  public search results, and every repo is re-checked to be public.

Stdlib only. Needs GITHUB_TOKEN in the environment.
"""

import datetime as dt
import html
import json
import os
import pathlib
import re
import urllib.parse
import urllib.request

LOGIN = "kaze-fuutu"
SELF_REPO = f"{LOGIN}/{LOGIN}"
ROOT = pathlib.Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
WORK_EVENTS = {"PushEvent", "PullRequestEvent", "CreateEvent", "IssuesEvent",
               "PullRequestReviewEvent", "ReleaseEvent"}
FALLBACK = '<b><a href="https://fuutu.com">Fuutu Stack</a></b>'


def request(url, body=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-live"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


_public_cache = {}


def is_public(full_name):
    if full_name not in _public_cache:
        try:
            _public_cache[full_name] = not request(f"{API}/repos/{full_name}")["private"]
        except Exception:
            _public_cache[full_name] = False
    return _public_cache[full_name]


def calendar_days():
    query = """query($login:String!){user(login:$login){contributionsCollection{
      contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"""
    data = request(f"{API}/graphql", {"query": query, "variables": {"login": LOGIN}})
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [(dt.date.fromisoformat(d["date"]), d["contributionCount"])
            for w in weeks for d in w["contributionDays"]]


def stats(days, today):
    counts = {d: c for d, c in days if d <= today}
    streak, day = 0, today
    if counts.get(day, 0) == 0:
        day -= dt.timedelta(days=1)  # today may simply not have started yet
    while counts.get(day, 0) > 0:
        streak += 1
        day -= dt.timedelta(days=1)
    week = sum(c for d, c in counts.items() if (today - d).days < 7)
    month = sum(c for d, c in counts.items() if (today - d).days < 30)
    return streak, week, month


def current_repo():
    events = request(f"{API}/users/{LOGIN}/events/public?per_page=50")
    for ev in events:
        name = ev["repo"]["name"]
        if ev["type"] in WORK_EVENTS and name != SELF_REPO and is_public(name):
            return name
    return None


def merged_prs(limit=3):
    q = f"author:{LOGIN} is:pr is:merged is:public -repo:{SELF_REPO}"
    url = f"{API}/search/issues?q={urllib.parse.quote(q)}&sort=updated&per_page=10"
    out = []
    for item in request(url).get("items", []):
        repo = item["repository_url"].split("/repos/", 1)[1]
        if is_public(repo):
            out.append((repo, item["title"], item["html_url"]))
        if len(out) == limit:
            break
    return out


def card(streak, week, month, dark):
    fg, mute, line, bg = (("#F4F4F2", "#8B8B90", "#232327", "#0D0D0F") if dark
                          else ("#0D0D0F", "#6B6B70", "#E4E4E2", "#FFFFFF"))
    teal = "#2FD4A7" if dark else "#0E9F7A"
    sans = "ui-sans-serif,-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
    mono = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
    cols = [(f"{streak}", "day streak"), (f"{week}", "contributions · 7 days"),
            (f"{month}", "contributions · 30 days")]
    cells = []
    for i, (num, label) in enumerate(cols):
        x = 40 + i * 380
        cells.append(
            f'<text x="{x}" y="128" fill="{fg}" font-family="{mono}" font-size="44" '
            f'font-weight="600">{num}</text>'
            f'<text x="{x}" y="160" fill="{mute}" font-family="{sans}" font-size="15" '
            f'letter-spacing="0.4">{label}</text>')
        if i:
            cells.append(f'<rect x="{x - 30}" y="88" width="1" height="76" fill="{line}"/>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 200" width="100%" role="img" aria-label="Kaze live: {streak} day streak, {week} contributions in 7 days, {month} in 30 days">
  <rect x="0.5" y="0.5" width="1199" height="199" rx="16" fill="{bg}" stroke="{line}"/>
  <circle cx="48" cy="44" r="5" fill="{teal}"/>
  <circle cx="48" cy="44" r="5" fill="none" stroke="{teal}" stroke-width="2">
    <animate attributeName="r" values="5;14" dur="2s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.8;0" dur="2s" repeatCount="indefinite"/>
  </circle>
  <text x="66" y="49" fill="{teal}" font-family="{mono}" font-size="13" font-weight="600" letter-spacing="2">ONLINE · 24/7</text>
  <text x="1160" y="49" text-anchor="end" fill="{mute}" font-family="{mono}" font-size="13" letter-spacing="1">LIVE · UPDATES ITSELF</text>
  {''.join(cells)}
</svg>
"""


def picture(name, alt):
    return (f'<picture>\n  <source media="(prefers-color-scheme: dark)" '
            f'srcset="./assets/{name}-dark.svg" />\n  <img src="./assets/{name}-light.svg" '
            f'alt="{alt}" width="100%" />\n</picture>')


def main():
    now = dt.datetime.now(dt.timezone.utc)
    streak, week, month = stats(calendar_days(), now.date())
    for dark in (True, False):
        (ROOT / "assets" / f"live-{'dark' if dark else 'light'}.svg").write_text(
            card(streak, week, month, dark))

    repo = current_repo()
    current = (f'<b><a href="https://github.com/{repo}">{html.escape(repo)}</a></b>'
               if repo else FALLBACK)
    lines = [picture("live", f"{streak} day streak, {week} contributions in 7 days"), "",
             f'<p align="center">Currently working on {current}</p>']
    prs = merged_prs()
    if prs:
        items = " · ".join(f'<a href="{u}">{html.escape(t)}</a> <sub>{html.escape(r)}</sub>'
                           for r, t, u in prs)
        lines.append(f'<p align="center"><sub>Recently merged</sub><br>{items}</p>')
    lines.append(f'<p align="center"><sub>Updated {now:%d %b %Y}</sub></p>')

    block = "\n".join(lines)
    text = README.read_text()
    text = re.sub(r"<!-- LIVE:START -->.*?<!-- LIVE:END -->",
                  lambda m: f"<!-- LIVE:START -->\n{block}\n<!-- LIVE:END -->", text, flags=re.S)
    README.write_text(text)


if __name__ == "__main__":
    main()
