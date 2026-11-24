# Live section

`workflows/live.yml` runs every three hours (and on demand) and calls `scripts/update_live.py`, which rewrites the block between `<!-- LIVE:START -->` and `<!-- LIVE:END -->` in the profile README plus `assets/live-{light,dark}.svg`.

| Item | Source | Privacy |
|---|---|---|
| Day streak, 7/30-day contributions | GraphQL contribution calendar | counts only, no repo names |
| Currently working on | public events of `kaze-fuutu` | repo re-checked as public; falls back to Fuutu Stack |
| Recently merged | search `is:pr is:merged is:public` | repo re-checked as public; hidden when empty |

Uses the repo's own `GITHUB_TOKEN`, pushes to `profile`, commits only when something changed.
