# AGENT.md — project logic, design system & rules

Single source of truth for **how this project looks and how work is done here**.
Read this before doing any UI/design work. Follow the rules exactly, stay inside
the scope described, and append to the change log at the bottom when you finish a
piece of work. The goal is that a fresh session can continue without guessing or
inventing patterns that don't belong.

---

## 1. What this project is

A weather-analytics product that helps a user **find the ideal European city for a
holiday**. Data flows:

```
Open-Meteo API → raw → staging → intermediate → marts (MotherDuck) → Streamlit dashboard
```

- Warehouse / database: MotherDuck, `open_meteo_europe_sa` (never `open_meteo_europe`).
- Dashboard entry point: `dashboard/app.py`.
- Theme/design module: `dashboard/utils/theme.py` (the only place styling is defined).
- Data access: `dashboard/utils/db.py` (read-only, cached, reads the `marts` schema).
- Run locally: `streamlit run dashboard/app.py` (needs `MOTHERDUCK_TOKEN` in `.env`).

Pages and the mart each one reads:

| Page | Reads | Status |
|------|-------|--------|
| Overview | `mart_latest_conditions`, `mart_forecast_upcoming` | Redesigned |
| Map | `dim_location`, `mart_latest_conditions` | **Next** |
| Forecast & trends | `mart_forecast_upcoming`, `fct_city_weather_day` | Old styling |
| Comparison | `fct_city_weather_day`, `mart_latest_conditions` | Old styling |
| Recommendations | `mart_latest_conditions` | Old styling |
| City detail | `mart_latest_conditions`, `fct_city_weather_day` | Old styling |

---

## 2. Design system — the "framer"

The whole app uses **one** design language: **Revolut** (sleek fintech; flat depth,
cobalt accent, precise typography). All pages share this system — see §4 for the
per-page approach. `dashboard/utils/theme.py` is the runtime source of truth for
every token below; add new tokens there, never hardcode colors elsewhere.

### Colors (tokens)

- Primary / brand: `#494fdf` (cobalt violet). Featured surfaces use solid cobalt with white text.
- Light mode: canvas `#f4f4f4`, surface `#ffffff`, hairline `#e2e2e7`, text `#191c1f`, muted `#505a63`, faint `#8d969e`.
- Dark mode: canvas `#0a0a0a`, surface `#16181a`, hairline `rgba(255,255,255,0.12)`, text `#ffffff`, muted `rgba(255,255,255,0.72)`, faint `#8d969e`.
- Semantic roles (used for score bars + condition pills): good = teal `#00a87e`, warn = amber `#ec7e00`, bad = red `#e23b4a`, rain/cold = blue `#376cd5`, neutral = gray `#8d969e`. Each has mode-specific pill bg/text pairs in `theme.py`.
- Visit-score thresholds: `>= 70` good, `>= 45` warn, else bad; missing/NaN → neutral.

### Typography

- Display / headings / numbers: **Space Grotesk** (weights 400, 500).
- Body / UI / captions: **Inter** (400, 500).
- Never require Aeonik Pro (Revolut's real face) — it's proprietary/paid. Space Grotesk is the license-safe substitute.
- Only weights 400 and 500. Sentence case everywhere; no ALL CAPS (letter-spacing is fine for eyebrow labels).

### Iconography

- **No emojis anywhere** — not in the UI, tab labels, page titles, or copy.
- Use **Tabler outline line icons** (loaded via CDN). Conditions get a line icon + a colored pill.

### Motion

- Subtle CSS-only micro-animations: card hover-lift (`translateY(-3px)`), score bars grow from 0 on load, hero/cards fade-in. ~200 ms, ease-out. Keep it restrained.

### Depth, shape, layout

- **Flat** — no drop shadows, gradients, blur, or glow. Depth comes from surface-luminance shifts + hairlines (Revolut's own rule).
- Radius: cards `20px`, pills/bars `999px`.
- Cards are elevated surfaces on the canvas, separated by a hairline (this is what fixes low card/background contrast).
- Content fills the full canvas (`.block-container` max-width `100%`, even side padding).
- Card grid = centered flex; rows fill the width and any trailing/orphan card is centered, never stranded.

### Modes

- Light (**default**) and dark, switchable at runtime via the header toggle. Every change must stay legible in both modes.

---

## 3. UI/UX patterns & decisions

- All styling is authored in **`theme.py`** and injected once (globally in `app.py`) via `st.markdown`. Do not scatter CSS across pages or duplicate tokens.
- Reusable component builders return HTML strings (e.g. `hero()`, `kpi_card()`); pages compose them.
- Header carries the brand + tagline, the light/dark toggle, and a **Fullscreen** button.
- **Top pick is shown once**: it headlines the hero and is excluded from the "current conditions" card grid. Exclusion is keyed off the highest `visit_score`, so it updates automatically when data reloads.
- Always round displayed numbers; render missing/NaN as `—` and a zero-width score bar.

---

## 4. Per-page approach

- **Shared theme, layout per page.** Every page uses the same tokens/fonts/motion from `theme.py`; only the layout and components differ.
- Redesign **one page at a time**, and **get the user's sign-off on the visual before implementing** a new page.
- Roadmap: Overview (done) → **Map (next)** → Recommendations → Forecast & trends → Comparison → City detail (order can change at the user's request).
- When theming charts/maps (Plotly, pydeck): transparent backgrounds, cobalt accents, themed text — match the tokens, no emojis, no default library chrome that clashes.

---

## 5. Hard rules (do not break)

1. **All code is written in Python.** Styling/CSS is authored in Python and injected via `st.markdown` / `theme.py` — no separate JS/TS/CSS build pipeline. When a browser-only action genuinely needs JavaScript (e.g. fullscreen), keep it to a minimal Streamlit component that is still created and wired from Python.
2. **No emojis** anywhere in the UI or output.
3. Use **only** the Revolut tokens defined in `theme.py`. Don't invent new colors or fonts; if a new token is needed, add it to `theme.py`.
4. **One page at a time**, with user sign-off on the look before building.
5. **Preview before committing.** Show the user a faithful visual preview in chat and get approval before committing any UI change. (The dev environment can't run Streamlit/MotherDuck live, so render an inline mockup that reuses the real `theme.py` tokens/markup.)
6. Keep concerns separate: don't modify dbt models / the data pipeline while doing UI work (or vice-versa) unless asked.
7. Commits & PRs: **no Claude / AI attribution** (no `Co-Authored-By`, no "Generated with…"). Keep each PR focused on one concern.
8. Database name is `open_meteo_europe_sa`. Never reintroduce `open_meteo_europe`.
9. Every change must remain legible in **both** light and dark mode.

---

## 6. Change log

Newest first. Describe **what** changed and **why**; do not include who did it.

- 2026-07-01 — Recommendations page redesigned to the theme: removed all emojis (medals, activity presets, title); activity presets renamed to plain text (Beach day / Hiking / City walk / Skiing) that drive the temp/rain/wind weight sliders via session_state. The leaderboard is now a top-pick cobalt hero (like the Overview) plus clean ranked rows (rank, city, condition pill, N/100 bar). Score breakdown is a themed stacked bar (cobalt/teal/amber); best-day finder is a themed table with score bars and condition pills. Preferences and filters live in themed cards; cities capped at 6.
- 2026-07-01 — Comparison page redesigned to the theme: dropped the red-yellow-green heatmap and emoji title. A **Line / Radar chart toggle** — Line (default) is a full-width multi-line chart (6-color series, legend, unified hover) with the metric table stacked below to fill the vertical space; Radar is a themed Scatterpolar (0–100 normalized axes) shown beside the metric table to fill the width. The metric-comparison table has in-cell magnitude bars (visit-score cell colored by score). Scope + city filters (capped at 6) in a themed filter bar. Added `theme.SERIES` (6 mode-aware series colors) and leaderboard/cell-bar CSS.

- 2026-07-01 — Forecast chart revised for legibility: the focus-city + gray-context approach was hard to read (indistinguishable gray lines, no legend). Replaced with up to **4 cities max** (enforced via `st.multiselect(max_selections=4)`), each drawn in a distinct mode-aware color with a **legend** and a unified hover that lists all selected cities at a date. High–low band now only shows when a single city is selected. Default selection is the top 4 cities by mean visit score.
- 2026-07-01 — Forecast & trends page redesigned: the overlaid multi-line chart (unreadable with 12 cities + high–low bands) is replaced by a focus-city view — one chosen city bold in cobalt with its high–low band, all others as thin gray context lines (Plotly, themed, transparent bg). Small-multiples toggle now facets one mini chart per selected city. The raw dataframe is replaced by a custom themed table (condition pills + visit-score bars) via new reusable `theme.condition_pill()` / `theme.score_bar()` helpers, and the filters live in a themed filter bar. All `st.container(border=True)` blocks now render as themed cards.
- 2026-07-01 — Overview/Map polish: uniform 4-per-row (responsive 3/2/1) equal-height card grid with a bottom-pinned footer so cards match even without a sparkline; enlarged cards; taller Leaflet map (700px); circular maximize-icon Fullscreen button; visit scores shown as N/100 in the hero and cards.
- 2026-07-01 — Map page redesigned to the shared theme: replaced pydeck with Folium (Leaflet) on OpenStreetMap/CartoDB tiles that follow the light/dark toggle, cobalt markers that scale and color by the selected variable, dark hover tooltip + click popup info-card + themed legend, and a themed filter bar (variable segmented control, forecast date, condition, min visit score). Added `folium` + `streamlit-folium` deps and a `.streamlit/config.toml` setting the cobalt `primaryColor` so native widgets match the brand.
- 2026-07-01 — Overview: excluded the current top-pick city from the card grid (it already headlines the hero), keyed off highest `visit_score` so it updates on reload. Leaves 12 cards, which grid evenly.
- 2026-07-01 — Overview layout: content now fills the full canvas (removed the 1180px cap), cards use a centered flex grid so trailing cards are centered instead of stranded, added a Fullscreen button beside the theme toggle, and set the default mode to Light.
- 2026-07-01 — Overview redesigned with the Revolut light/dark theme: new `dashboard/utils/theme.py` (tokens, runtime toggle, `hero()`/`kpi_card()` builders), line-icon + colored condition pills replacing emojis, Space Grotesk display type, elevated hairline-separated KPI cards (fixes low contrast), and subtle CSS micro-animations. Theme injected globally in `app.py`; emojis removed from title and tab labels.
