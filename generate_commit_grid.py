"""
Generates dist/commit-count-grid.svg and commit-count-grid-dark.svg:
a GitHub-style contribution grid where each day's cell fades/scales in
in sequence (column by column, like the snake eating), and shows the
exact commit count as a label once "revealed".

Note: GitHub sanitizes <script> tags out of SVGs embedded in READMEs,
so the animation is done with SMIL (<animate>/<animateTransform>),
the same technique Platane/snk itself uses for the snake. That means
we can't literally hook into the snake's internal timing, but we use
the same total duration and left-to-right/column-by-column stagger so
the two animations *feel* synced when placed one above the other.
"""

import os
import json
import requests

GH_TOKEN = os.environ["GH_TOKEN"]
USERNAME = os.environ["GH_USERNAME"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

def fetch_calendar():
    resp = requests.post(
        "https://api.github.com/graphql",
        headers={"Authorization": f"bearer {GH_TOKEN}"},
        json={"query": QUERY, "variables": {"login": USERNAME}},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"]))
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]


def color_for(count, palette):
    if count == 0:
        return palette[0]
    if count < 3:
        return palette[1]
    if count < 6:
        return palette[2]
    if count < 10:
        return palette[3]
    return palette[4]


PALETTES = {
    "light": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
    "dark":  ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
}

CELL = 12
GAP = 3
LABEL_FONT_SIZE = 6
TOTAL_DUR = 8  # seconds, roughly matches snk's default snake duration


def build_svg(weeks, theme):
    palette = PALETTES[theme]
    bg = "#0d1117" if theme == "dark" else "#ffffff"
    text_color = "#c9d1d9" if theme == "dark" else "#24292f"

    n_weeks = len(weeks)
    width = n_weeks * (CELL + GAP) + GAP
    height = 7 * (CELL + GAP) + GAP + 20

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<rect width="100%" height="100%" fill="{bg}" rx="6"/>',
        f'<text x="{GAP}" y="12" font-family="Segoe UI, sans-serif" font-size="10" '
        f'fill="{text_color}">Daily commits — count-up reveal</text>',
    ]

    total_days = sum(len(w["contributionDays"]) for w in weeks)
    day_index = 0

    for wi, week in enumerate(weeks):
        for di, day in enumerate(week["contributionDays"]):
            count = day["contributionCount"]
            x = GAP + wi * (CELL + GAP)
            y = 20 + GAP + di * (CELL + GAP)
            fill = color_for(count, palette)

            # stagger begin time so cells reveal column-by-column, left to right,
            # mirroring the direction the snake travels across the grid
            begin = (wi / max(n_weeks - 1, 1)) * (TOTAL_DUR * 0.85)

            parts.append(
                f'<g opacity="0" transform="scale(0.4)" '
                f'style="transform-origin:{x + CELL/2}px {y + CELL/2}px">'
                f'<animate attributeName="opacity" from="0" to="1" '
                f'begin="{begin:.2f}s" dur="0.4s" fill="freeze"/>'
                f'<animateTransform attributeName="transform" type="scale" '
                f'from="0.4" to="1" begin="{begin:.2f}s" dur="0.4s" '
                f'fill="freeze" additive="replace"/>'
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{fill}">'
                f'<title>{day["date"]}: {count} commit{"s" if count != 1 else ""}</title>'
                f'</rect>'
            )

            if count > 0:
                parts.append(
                    f'<text x="{x + CELL/2}" y="{y + CELL/2 + 2}" '
                    f'font-family="Segoe UI, sans-serif" font-size="{LABEL_FONT_SIZE}" '
                    f'text-anchor="middle" fill="{text_color}">{count}</text>'
                )
            parts.append("</g>")
            day_index += 1

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    weeks = fetch_calendar()
    os.makedirs("dist", exist_ok=True)

    with open("dist/commit-count-grid.svg", "w") as f:
        f.write(build_svg(weeks, "light"))

    with open("dist/commit-count-grid-dark.svg", "w") as f:
        f.write(build_svg(weeks, "dark"))

    print("Generated dist/commit-count-grid.svg and dist/commit-count-grid-dark.svg")


if __name__ == "__main__":
    main()
