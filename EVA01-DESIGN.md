# EVA-01 — UI Theme & Component Spec

A portable design system for building **new** interfaces and components in the EVA-01 visual language.
Written to be handed to a coding agent (Claude, Codex, Cursor, etc.) alongside a product brief.

Version 1.0 · Applies to any concept: dashboards, editors, marketing pages, mobile shells, docs.

---

## 0. How to use this file

Read sections 1–3 before writing any code. They define what is invariant. Sections 4–8 are the
vocabulary. Section 9 is the procedure for a concept you have not seen before. Section 11 is the
checklist you must pass before calling the work done.

Machine-readable companions, if you prefer values over prose:

- `eva01-tokens.css` — CSS custom properties, drop-in.
- `eva01-tokens.json` — same values as JSON for build pipelines.

If a value is needed that is not in this document, derive it from the nearest token in section 2
and say so in a comment. Do not invent a new hue.

---

## 1. The concept

An industrial command interface: near-black instrument panels, one structural purple, one
high-voltage green that means "this is live", and warning amber reserved for hazard.

The language is **technical, angular and restrained**. Density is high, ornament is geometric,
and colour is information. It should read like equipment that is being operated, not a website
that is being browsed.

Four properties carry the identity, in order of importance:

1. **A dark, violet-biased neutral field.** Never pure black, never grey — every surface has a
   small amount of purple in it.
2. **One accent.** Neon green. It marks the active, the primary, the connected. Nothing else.
3. **Hard edges.** Radii of 1–2px. Strokes of exactly 1px. Panels are rectangles, not cards with
   soft corners.
4. **A thin layer of instrument furniture.** Corner brackets, hazard striping, hairline rules,
   monospace telemetry labels. This is applied at the *frame*, never to the content inside it.

---

## 2. Colour system

### 2.1 Surfaces (the only five backgrounds you may use)

| Token | Hex | Use |
|---|---|---|
| `--surface-void` | `#05030B` | App backdrop, artboard, area outside the main frame, modal scrim base |
| `--surface-base` | `#0C0818` | Default app/page background |
| `--surface-panel` | `#16102C` | Cards, node bodies, table containers, panels |
| `--surface-raised` | `#1E1640` | Inputs, chips, hover rows, secondary buttons, popovers |
| `--surface-overlay` | `#2A1F4E` | Active nav item, selected row, tooltip-on-dark, dragged state |

Elevation is expressed by stepping one rung up the ladder, plus a 1px border. Shadows are used
only for floating layers (modals, dropdowns, the selected node), never for flat cards.

### 2.2 Structure and accents

| Token | Hex | Use |
|---|---|---|
| `--line-hairline` | `#2E2150` | Default 1px borders, dividers |
| `--line-strong` | `#3D2C68` | Emphasised borders, panel edges, dashed placeholders |
| `--purple-deep` | `#3A1D66` | Header bands, structural frames, section headers |
| `--purple` | `#6B3FA0` | Fills that must read as "brand" (bars, tabs, banner) |
| `--purple-light` | `#7B4BB8` | Secondary data series, hover on purple fills |
| `--accent` | `#A6FF3D` | **Primary action, active state, connected/selected, focus ring** |
| `--accent-dim` | `#7BBF35` | Accent borders that should not glow |
| `--on-accent` | `#0B1206` | Text on any accent-green fill. Never white on green |
| `--warn` | `#FFC24B` | Caution, hazard striping, degraded state |
| `--alert` | `#FF7A1A` | Escalation, quota, "attention needed" |
| `--danger` | `#FF2E4D` | Destructive action, error, disconnected |
| `--info` | `#9A6BFF` | Neutral informational accent, third data series |

**The accent budget.** On any single screen, neon green may appear in at most three places:
the primary action, the current selection, and one status indicator. If green is already on the
primary button, do not use it for links, headings or badges on the same screen.

### 2.3 Text ramp

Four steps. Pick by hierarchy, not by contrast preference.

| Token | Hex | Use | Contrast on `--surface-base` |
|---|---|---|---|
| `--text-primary` | `#F7F4FF` | Headings, values, active labels | 18.2 : 1 |
| `--text-secondary` | `#DCD3F5` | Body copy, descriptions, inactive-but-important | 13.8 : 1 |
| `--text-tertiary` | `#B9AEDC` | Supporting labels, secondary metadata | 9.5 : 1 |
| `--text-meta` | `#8B80AE` | Placeholders, mono telemetry, timestamps, units | 5.5 : 1 |

All four pass WCAG AA on `--surface-base` and `--surface-panel`. On `--surface-overlay`, do not
go below `--text-tertiary`.

Text on a light or accent fill: use `--on-accent` (`#0B1206`) on green, `#1A0A22` on amber.
**Never place white text on the accent green.**

### 2.4 Data series (charts, graphs, legend)

In fixed order, for maximum separation on dark:

```
1 #A6FF3D  green     2 #9A6BFF  violet    3 #FFC24B  amber
4 #FF7A1A  orange    5 #FF2E4D  red       6 #6B5F92  muted slate
```

Grid lines `#2E2150`, axis labels `--text-meta` in Share Tech Mono 10. Never use a gradient in
a data series.

---

## 3. Typography

Three families, each with a job. All are free Google Fonts. Ship them or the layout drifts.

| Family | Role | Weights used |
|---|---|---|
| **Chakra Petch** | Display, titles, node headers, numbers that must read as instrumentation | 500, 600, 700 |
| **Rajdhani** | All UI text: labels, buttons, body, table cells | 500, 600, 700 |
| **Share Tech Mono** | Telemetry only: field labels, meta, units, code, timestamps, IDs | 400 |

Fallback stack: `"Chakra Petch", "Rajdhani", "Share Tech Mono", system-ui, sans-serif`.

### 3.1 Scale

| Token | Size / line | Family | Weight | Case & tracking | Use |
|---|---|---|---|---|---|
| `--type-micro` | 9 / 12 | Mono | 400 | UPPER, `+0.06em` | Field labels, units, IDs, captions |
| `--type-label` | 11 / 14 | Rajdhani | 600 | UPPER, `+0.045em` | Buttons, tabs, nav, chips, table headers |
| `--type-body-s` | 12 / 18 | Rajdhani | 500 | sentence, `+0.01em` | Dense UI copy, table cells |
| `--type-body` | 13 / 20 | Rajdhani | 500 | sentence | Default body |
| `--type-body-l` | 15 / 22 | Rajdhani | 500 | sentence | Reading copy, descriptions |
| `--type-title-s` | 16 / 22 | Chakra Petch | 600 | UPPER, `+0.02em` | Card and node titles |
| `--type-title-m` | 20 / 26 | Chakra Petch | 600 | sentence | Section headings |
| `--type-display` | 32 / 34 | Chakra Petch | 700 | UPPER, `-0.01em` | Page titles, hero |
| `--type-display-xl` | 44 / 44 | Chakra Petch | 700 | UPPER, `-0.015em` | Marketing, title screens |
| `--type-mono-data` | 12 / 16 | Mono | 400 | sentence, `+0.02em` | Code, JSON, IDs |

### 3.2 Case rules

- Uppercase is for **labels, titles and navigation only** — strings of roughly 24 characters or
  fewer. Never uppercase a sentence, a paragraph, a description or a tooltip.
- Uppercase text always gets positive tracking (0.045em at 11px, 0.02em at 16px+).
- Numerals in dashboards use Chakra Petch or Share Tech Mono so figures align to a grid.
- If a label must be uppercased inside a fixed-width control and it would overflow, reduce the
  size by at most 25% before allowing it to truncate. Never let an uppercase label break the
  control's width.

---

## 4. Shape, spacing, grid

**Radii.** `--radius-xs: 1px`, `--radius-sm: 2px`, `--radius-md: 3px`. That is the whole scale.
Nothing above 3px except avatars and circular icon buttons (999px). Pills with 10px+ radii do not
belong in this system — a "pill" here is a 2px-radius rectangle.

**Strokes.** Exactly 1px for all borders. 2px only for accent rules and corner brackets. Never
use a stroke heavier than 2px.

**Spacing scale (4px base):** 2, 4, 8, 12, 16, 20, 24, 32, 40, 56, 72.
Default gap between related items 8; between groups 16; panel padding 16 or 20; section rhythm 32.

**Control heights:** 24 (micro), 28 (compact), 32 (default), 36 (comfortable), 40 (touch).
One height per context — do not mix 28 and 36 in the same toolbar.

**Grid.** 12 columns, 24px gutter, 1280px max content width for app shells; 720px measure for
reading. Dashboards run dense: 8px row rhythm inside tables.

**Corner brackets.** Optional frame furniture: 2px lines, 24–30px long, in `--accent`, placed at
the four corners of the outermost frame, inset 0px. One set per screen. Never on cards.

---

## 5. Effects

Effects are seasoning. One glow per screen, maximum.

| Token | Value | Use |
|---|---|---|
| `--glow-accent` | `0 0 18px rgba(166,255,61,0.55)` | Primary action hover, selected node, live indicator |
| `--glow-accent-strong` | `0 0 26px rgba(166,255,61,0.65)` | The single most important element on screen |
| `--glow-soft` | `0 0 46px rgba(107,63,160,0.45)` | Floating panel / modal halo |
| `--shadow-float` | `0 8px 24px rgba(0,0,0,0.55)` | Modals, dropdowns, popovers |
| `--focus-ring` | `0 0 0 1px #A6FF3D, 0 0 0 3px rgba(166,255,61,0.25)` | Keyboard focus, always visible |

**Scanlines** (whole-screen CRT texture, optional, decorative only):

```css
background-image: repeating-linear-gradient(180deg,
  rgba(255,255,255,0.032) 0 1px, transparent 1px 12px);
```

Never put scanlines behind text smaller than 12px, never above 5% opacity, never on a form
where the user is reading carefully.

**Hazard stripe** (a strip, 10–12px tall, never a fill for a large area):

```css
background-image: repeating-linear-gradient(45deg,
  #FFC24B 0 10px, #141024 10px 20px);
```

One hazard strip per screen, pinned to a frame edge — top of a modal, bottom of a page, edge of a
destructive zone. It is a warning signal; using it decoratively devalues `--warn`.

**Glow rules.** Glow means *live*, not *pretty*. It goes on the active/primary element only.
Never glow body text, never glow a card that is not selected, never stack two glows.

---

## 6. Component recipes

Every recipe below is complete. Compose new components from these primitives rather than
inventing new values.

### Button

| Variant | Fill | Border | Text | Hover | Active |
|---|---|---|---|---|---|
| Primary | `--accent` | none | `--on-accent`, `--type-label` | `--glow-accent`, brightness 1.05 | translateY(1px), brightness 0.92 |
| Secondary | transparent | 1px `--accent-dim` | `--accent` | bg `rgba(166,255,61,0.08)` | bg `rgba(166,255,61,0.14)` |
| Neutral | `--surface-raised` | 1px `--line-hairline` | `--text-secondary` | border `--line-strong`, text `--text-primary` | bg `--surface-overlay` |
| Ghost | transparent | none | `--text-tertiary` | bg `--surface-raised`, text `--text-primary` | bg `--surface-overlay` |
| Destructive | transparent | 1px `--danger` | `--danger` | bg `rgba(255,46,77,0.12)` | bg `rgba(255,46,77,0.20)` |

Height 32, padding 0 14, radius 2, gap 8 between icon and label. Disabled: opacity 0.38,
no glow, `cursor: not-allowed`. Icon buttons: 32×32, radius 2, same fill rules as Ghost.

### Input / Select / Textarea

Background `--surface-void`, 1px `--line-hairline`, radius 2, height 34, padding 0 10,
text `--text-primary` at `--type-body-s`. Placeholder `--text-meta`.
Focus: border `--accent` + `--focus-ring`. Error: border `--danger`, helper text `--danger` at
`--type-micro`. Disabled: bg `--surface-base`, text `--text-meta`, opacity 0.7.

Field label sits above the control: Share Tech Mono 9, uppercase, `+0.06em`, `--text-meta`,
margin-bottom 4. Units and optional markers go to the right of the label in the same style.

### Chip / Badge

Height 20, padding 0 8, radius 2, `--type-micro` uppercase.
Default: bg `--surface-raised`, border 1px `--line-hairline`, text `--text-tertiary`.
Accent: transparent bg, border `--accent-dim`, text `--accent`.
Warning: transparent bg, border `--warn`, text `--warn`.
Danger: transparent bg, border `--danger`, text `--danger`.
Status dot: 6px square (not a circle) in the variant colour, 6px before the label.

### Panel / Card

Background `--surface-panel`, 1px `--line-hairline`, radius 3, padding 16.
Optional header row: height 36, `--type-label` uppercase `--text-tertiary`, bottom border 1px
`--line-hairline`. Selected state: border `--accent` + `--glow-accent`.

### Node (canvas / graph item)

Width 200–280, background `--surface-panel`, border 1px `--line-strong`, radius 3.
Title row: 32px, `--type-title-s` in `--accent`, uppercase, with a 2px accent rule beneath.
Body rows: field label (mono micro) + value (`--type-body-s`).
Ports: 8px squares on the left/right edge, `--accent` when connected, `--line-strong` when free.
Selected: border `--accent`, `--glow-accent`, plus 2px corner brackets at the four corners.
Connectors: 1px `--line-strong`; animated dashes in `--accent` while data is flowing.

### Tab bar

Container: bg `--purple-deep` (app header) or transparent, bottom border 1px `--line-strong`.
Inactive tab: `--type-label`, `--text-tertiary`, padding 0 12, height 28.
Active tab: bg `--accent`, text `--on-accent`, radius 2. Alternative active style for dense
contexts: 2px `--accent` underline, text `--text-primary`, no fill.
Hover (inactive): text `--text-secondary`, bg `rgba(166,255,61,0.06)`.

### Table

Header: `--type-micro` uppercase `--text-meta`, height 32, bottom border 1px `--line-strong`.
Row: height 36–40, border-bottom 1px `--line-hairline`, text `--text-secondary`.
Hover: bg `--surface-raised`. Selected: bg `--surface-overlay`, left 2px `--accent` bar.
Numeric cells: right-aligned, Chakra Petch, `--text-primary`. Never zebra-stripe — use hairlines.

### Sidebar / Nav item

Height 32, padding 0 12, radius 2, `--type-label`, `--text-tertiary`.
Hover: bg `--surface-raised`, text `--text-primary`.
Active: bg `--surface-overlay`, text `--text-primary`, 2px `--accent` bar on the leading edge.
Section headings: `--type-micro` uppercase `--text-meta`, margin 16 0 8.

### Modal / Dialog

Scrim `rgba(5,3,11,0.78)` + `backdrop-filter: blur(2px)`.
Panel: bg `--surface-panel`, 1px `--line-strong`, radius 3, `--shadow-float` + `--glow-soft`.
Title bar 48px: `--type-title-s` uppercase, bottom border 1px `--line-hairline`, close control
on the right as a Ghost icon button. Optional hazard strip along the panel's top edge, full width.
Footer: right-aligned actions, 12px gap, top border 1px `--line-hairline`, padding 12 16.

### Toast / Alert

Height auto, min 44, bg `--surface-raised`, 1px `--line-hairline`, radius 2, padding 10 14,
text `--type-body-s`. Leading 2px bar in the semantic colour (accent / warn / danger / info).
Icon 14px, mono label for the timestamp. Stack bottom-right, 8px gap, max 3 visible.

### Tooltip

bg `--surface-void`, 1px `--line-strong`, radius 2, padding 6 8, text `--text-secondary` at
Share Tech Mono 10, max-width 240. No arrow, or a 4px square notch. No shadow.

### Toggle, checkbox, radio

Toggle: track 28×14, radius 2, off `--line-hairline`, on `--accent`; knob 10×10, radius 1,
off `--text-meta`, on `--on-accent`. Checkbox: 14×14, radius 1, checked bg `--accent` with
`--on-accent` tick. Radio stays circular (the one place a circle is correct), 14px, ring
`--line-strong`, selected centre dot `--accent`.

### Progress / Loading

Track 2px `--line-hairline`, fill `--accent`, square ends, no radius. Indeterminate: 30% wide
accent bar sweeping left→right, 900ms linear, infinite. Skeleton: `--surface-raised` blocks with
a 1.6s opacity pulse between 0.5 and 0.9.

### Empty state

Dashed 1px `--line-strong` container, radius 2, padding 32, centred.
Headline `--type-label` uppercase `--text-tertiary`; body `--type-body-s` `--text-meta`.
One Secondary button. No illustration.

### Code block

bg `--surface-void`, 1px `--line-hairline`, radius 2, padding 12, Share Tech Mono 12/18.
Strings `--accent`, numbers `--warn`, keys `--info`, comments `--text-meta`.
Copy control as a Ghost icon button in the top-right.

---

## 7. States

| State | Treatment |
|---|---|
| Default | As specified per component |
| Hover | One rung up the surface ladder, or +6% brightness on accent fills. 120ms |
| Active / pressed | translateY(1px) or brightness 0.92. No colour change |
| Focus | `--focus-ring`, always visible, never removed for mouse users |
| Selected | `--surface-overlay` + 2px `--accent` leading bar, or border `--accent` for bordered items |
| Disabled | opacity 0.38, no glow, no hover response, `cursor: not-allowed` |
| Error | border `--danger`, message in `--danger` at `--type-micro` |
| Loading | content dims to 0.6, indeterminate bar or skeleton, control stays at fixed size |

---

## 8. Motion

Fast and mechanical. Nothing bounces, nothing overshoots.

- Micro (hover, focus, toggle): 120ms, `cubic-bezier(0.2, 0, 0, 1)`
- Standard (expand, tab switch, dropdown): 180ms, same easing
- Overlay (modal, drawer): 220ms in, 160ms out
- Data flow on connectors: 800–1200ms linear loop, dashes only
- Respect `prefers-reduced-motion`: keep opacity changes, drop transforms and loops

---

## 9. Applying this to a new concept

Work in this order. Do not start with decoration.

1. **Map the surfaces.** Decide which of the five surface tokens is the page background, which is
   the panel, which is the input. Every new concept needs exactly one of each; if you need a
   sixth background, you have mis-assigned one.
2. **Place the accent.** Find the single most important action or state on the screen and give it
   `--accent`. Everything else is neutral. Re-check the accent budget (max three green elements).
3. **Assign the ramp.** Primary/secondary/tertiary/meta to every text style you have. If a style
   does not fit a rung, you have one style too many.
4. **Set geometry.** Radii 1–3px, 1px borders, control heights from the scale.
5. **Add furniture last.** One hazard strip, one set of corner brackets, one scanline overlay —
   at the frame, never on the content. If in doubt, omit it.
6. **Verify** against section 11.

### What flexes by concept

| Concept | Adjust | Keep |
|---|---|---|
| Dense dashboard | Body 12/18, rows 32, mono for all numerals | All colours, all radii, accent budget |
| Editor / canvas | Node bodies on `--surface-panel`, grid dots `#5A4691` at 12–16px pitch | Purple structure, green for selection only |
| Marketing page | `--type-display-xl` allowed, one full-bleed purple band, longer measure (720px) | Dark field, hard edges, single accent |
| Mobile shell | Control heights 40, spacing +4, tabs become a bottom bar with 2px accent underline | Everything else |
| Docs / long-form | Body 15/24, `--text-secondary` default, mono only for code | Text ramp, hairlines |
| Data table heavy | Rows 32, mono numerals, no row hover glow | Hairline dividers, no zebra |

### Adding a component that is not in section 6

Build it from: one surface token, one 1px border token, one radius, one type token, at most one
accent. Then add the four states (hover, focus, selected, disabled) with the treatments in
section 7. If it needs a new colour to work, the design is wrong — re-map it.

---

## 10. Anti-patterns

- White text on `--accent` green. Use `--on-accent`.
- Green body copy, green headings, or green links on a screen that already has a green primary.
- Soft, rounded cards (radius 8+) or pill-shaped chips.
- Gradients on surfaces or buttons. Gradients belong to data visualisation only, and even there,
  prefer flat series colours.
- Drop shadows on flat cards. Shadows are for floating layers.
- Two or more glows on one screen.
- Hazard stripes used as decoration, or as a background fill for a large area.
- Uppercasing sentences, descriptions, tooltips or error messages.
- Zebra striping instead of hairline dividers.
- Light-mode variants. This system is dark only — if a light theme is demanded, treat it as a
  separate system, not a colour swap of this one.
- **Inventing terminology.** This system is visual only. Never rename the client's entities,
  features, states or labels, and never introduce lore-flavoured copy. Keep the product's own
  words and change only how they look.

---

## 11. Acceptance checklist

Before you call a screen done, confirm every line:

- [ ] Every background is one of the five surface tokens; no sixth value exists in the CSS.
- [ ] Neon green appears at most three times, and never as body text.
- [ ] No white text on green; `--on-accent` used on all accent fills.
- [ ] All radii are 1–3px (or 999px for avatars/circular icon buttons only).
- [ ] All borders are exactly 1px (2px only for accent rules and brackets).
- [ ] Every text style maps to a rung of the type scale; no ad-hoc font sizes.
- [ ] Uppercase used only on labels and titles, with tracking applied.
- [ ] Every interactive element has visible focus, hover, active and disabled states.
- [ ] Contrast: body text ≥ 4.5:1, meta ≥ 4.5:1, large display ≥ 3:1 against its own background.
- [ ] At most one glow and one piece of furniture (stripes / brackets / scanlines) per screen.
- [ ] No product wording changed, added or re-flavoured.

---

## 12. Priming prompt for a coding agent

Paste this above your brief:

> You are building UI in the EVA-01 theme. Read `EVA01-DESIGN.md` and `eva01-tokens.css` first and
> treat them as the single source of truth for colour, type, spacing, radius, states and effects.
> Use the CSS custom properties — do not hard-code hex values or font sizes. Compose new
> components only from the primitives in section 6, and give every interactive element the four
> states from section 7. The theme is visual only: keep the product's existing terminology and
> copy exactly as given, and do not introduce lore-flavoured naming. Before finishing, walk the
> section 11 checklist and report any line you could not satisfy.
