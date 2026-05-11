---
name: frontend_design_tty
description: >
  Design system for dark, terminal-inspired web UIs (monospace,
  mint/sage on dark blue-grey, box drawing, hex labels, no
  rounded corners). Provides concrete CSS custom properties +
  component patterns + anti-patterns. Use when a new web UI is
  built or extended in TTY aesthetic (Huddle, BuddyAI dashboards,
  comparable apps), or when an existing element needs a
  conformance check.
status: active
invocation:
  primary: user-facing
  secondary: [sub-skill]
  trigger_patterns:
    - "TTY-Aesthetic"
    - "TTY-Design"
    - "TTY-Style"
    - "Terminal-Pastell"
    - "Terminal-Style UI"
    - "wende TTY an"
    - "Hex-Label"
    - "Box-Drawing"
    - "Monospace-UI"
disable-model-invocation: false
uses: []
---

# Skill: frontend_design_tty

## Purpose

Visual identity for dark, terminal-inspired web UIs. **Not a retro
terminal emulator, not a hacker movie** — a contemporary app that takes
the structure and typography of terminal interfaces, softened with
pastel accents. *"The child of a Linux TTY and a calm late-night
coding session."*

The skill is a **design-system skill**, not a methodology skill: it
provides **concrete token values, component patterns and anti-patterns**.
Whoever invokes it gets a reference that translates directly into CSS /
components — not guidance on how to decide.

Used in **Huddle** (chat/voice/video, web app) and in
**BuddyAI dashboards** as the default aesthetic. Other projects can
adopt it equally.

## When to invoke

- Building a new web UI component / page / layout when the project
  explicitly declares TTY aesthetic (e.g., `intent.md` or
  `decisions.md` lists TTY style)
- Checking existing UI for TTY conformance (drift check before merge)
- Selecting design tokens (colours, spacing, type) — not from memory
- Setting up a theme variant (e.g., Amber Console, alternative accent
  palette)

### Do not invoke for

- **Generic production UI discipline** (component arch, state, 4
  states, a11y methodology) -> `frontend_ui_engineering`
- **UX spec review** (heuristic, IA, interaction) -> `spec_board mode=ux`
- **Code-diff review** of frontend changes -> `code_review_board`
  (with UX specialist personas)
- **Backend / API design** -> `api_and_interface_design`
- **Apps with a different aesthetic** (Material, Tailwind default,
  Glassmorphism, etc.) — TTY is opinionated, NOT a default

## Standalone rationale

Why a separate skill rather than a mode of `frontend_ui_engineering`
or a reference file?

- **`frontend_ui_engineering`** = generic methodology (what must
  happen during the build: file layout, container/presentation split,
  state tree, a11y patterns, 4 states). Design-system-agnostic — fits
  Material, Tailwind default, TTY, Glassmorphism alike.
- **`frontend_design_tty` (this skill)** = a concrete design system with
  **token values, component patterns and anti-patterns**. Methodology-
  agnostic — does not concern how a component is built, only how it
  looks.

The two complement each other: `frontend_ui_engineering` says *"build
an empty-state component with 4 states"*, `frontend_design_tty` says
*"use `--bg-elevated` as the background, a hex label as the header,
monospace 14px"*. Deleting and integrating would either narrow the
methodology to TTY or render the design system invisible.

Source: previously `skills/frontend_design_tty/SKILL.md` in
BuddyAI (2026-03-06), migrated into forge
(`skills/frontend_design_tty/SKILL.md`, 2026-04-15, commit `0e80cd0`).
Restore + restored 2026-05-07.

## Process

Application of the skill runs in 4 steps — applies to both new builds
and conformance checks.

### 1. Token setup (once per project)

Set up a `:root` block with the colour, typography, spacing and border
tokens from the reference blocks below. One theme = one complete token
set, no mixing.

- New component code references CSS vars EXCLUSIVELY, never raw hex.
- If the project wants multiple themes: `[data-theme="..."]` attribute
  on the root element + a theme block per variant (see Theme
  Architecture).

### 2. Pick a component pattern

For each component type (button, input, modal, sidebar, status
indicator, chat message, ...), adopt the matching pattern block from
§Component Patterns. For a deviating use case: document it in §Domain
Extension Points instead of overriding global tokens.

### 3. Conformance check

Before merge / PR submission, check against §Anti-Patterns. One
anti-pattern hit = block. Examples: rounded corners > 2px,
proportional fonts anywhere, drop shadows on cards, chat bubbles,
hardcoded hex.

### 4. Domain extension (optional)

Project-specific tokens (chat density, video aspect ratio, sidebar
width) as additional `--<domain>-*` CSS vars in the project theme
file, NOT here.

---

## Reference

FABRK (fabrk.dev) is the closest external reference — adopt the
structural vocabulary (hex labels, box drawing, monospace grid), but
replace the aggressive amber palette with the softer accent system
below.

---

## Color System

All colours as CSS custom properties. Use ONLY these — never raw hex
in components.

### Color tokens

```css
:root {
  /* -- Background Layers -- */
  --bg-base:       #1a1a2e;   /* primary background */
  --bg-surface:    #1f1f35;   /* cards, panels, sidebar */
  --bg-elevated:   #25253f;   /* modals, dropdowns, hover states */
  --bg-input:      #16162a;   /* input fields, code blocks */

  /* -- Primary Accent: Mint/Sage -- */
  --accent:        #a8d8b9;   /* primary — buttons, links, active states */
  --accent-dim:    #7ab892;   /* secondary — borders, subtle highlights */
  --accent-muted:  #4a7a5e;   /* tertiary — disabled states, inactive tabs */
  --accent-glow:   rgba(168, 216, 185, 0.15);  /* glow effects, focus rings */

  /* -- Text -- */
  --text-primary:  #e0e0e8;   /* main body text */
  --text-secondary:#8888a0;   /* labels, timestamps, metadata */
  --text-muted:    #555570;   /* placeholders, disabled text */
  --text-accent:   #a8d8b9;   /* links, active labels */

  /* -- Semantic -- */
  --error:         #e07070;   /* errors, destructive actions */
  --warning:       #d4b896;   /* warnings, caution states */
  --success:       #a8d8b9;   /* same as accent — confirmation, online */
  --info:          #89b4d4;   /* informational, help text */

  /* -- Borders -- */
  --border-default:#2a2a45;   /* subtle structural borders */
  --border-active: #a8d8b9;   /* focused/active element borders */

  /* -- Activity Indicators -- */
  --glow-speaking: rgba(168, 216, 185, 0.6);   /* avatar/element glow when active */
  --glow-ring:     0 0 0 3px rgba(168, 216, 185, 0.3);  /* focus/active ring */
}
```

### Theme architecture

The whole UI is theme-agnostic by construction — every visual value
flows through CSS vars, never hardcoded in components. Themes via the
`data-theme` attribute on the root element.

A theme redefines the complete token palette. Nothing else changes —
components, layout, spacing remain identical.

```css
/* Example: Amber Console theme */
[data-theme="amber"] {
  --bg-base:       #1a1510;
  --bg-surface:    #211c14;
  --bg-elevated:   #2a2319;
  --bg-input:      #15120c;
  --accent:        #d4a24c;
  --accent-dim:    #b8882e;
  --accent-muted:  #7a5a1e;
  --accent-glow:   rgba(212, 162, 76, 0.15);
  --text-primary:  #e8e0d0;
  --text-secondary:#a09078;
  --text-muted:    #6a5a48;
  --text-accent:   #d4a24c;
  --error:         #e07050;
  --warning:       #e8c870;
  --success:       #a8c870;
  --info:          #70a8d0;
  --border-default:#302818;
  --border-active: #d4a24c;
  --glow-speaking: rgba(212, 162, 76, 0.6);
  --glow-ring:     0 0 0 3px rgba(212, 162, 76, 0.3);
}
```

Theme support is optional. A project can start with a single palette
and add themes later — the architecture carries this without
refactoring, as long as components rely solely on vars.

### Color rules

- NEVER pure white (#ffffff). The brightest text is `--text-primary`.
- NEVER pure black (#000000). The darkest background is `--bg-input`.
- Use the accent colour sparingly. If everything is accent, nothing
  stands out. Primary use: interactive elements, active states, online
  indicators.
- Error red and warning amber are desaturated — they inform, they do
  not shout.
- Four background layers create depth without shadows or gradients.

---

## Typography

### Font stack

```css
:root {
  --font-mono: 'IBM Plex Mono', 'JetBrains Mono', 'Fira Code',
               'Cascadia Code', 'Consolas', monospace;
  --font-body: var(--font-mono);  /* monospace everywhere */
}
```

IBM Plex Mono is primary — best legibility at small sizes (13-14px).
JetBrains Mono as the first fallback. Load from Google Fonts or
self-host (weights: 400, 500, 700).

### Type scale

```css
:root {
  --text-xs:   0.75rem;    /* 12px — metadata, timestamps */
  --text-sm:   0.8125rem;  /* 13px — secondary labels, metadata */
  --text-base: 0.875rem;   /* 14px — body text, messages, inputs */
  --text-lg:   1rem;        /* 16px — section headers, room names */
  --text-xl:   1.25rem;     /* 20px — page titles, modal headers */
  --text-2xl:  1.5rem;      /* 24px — hero elements */
  --text-3xl:  1.875rem;    /* 30px — rare, landing/splash only */
  --text-4xl:  2.5rem;      /* 40px — rare, display type only */
}
```

### Type rules

- ALL text is monospace. No exceptions.
- Body text is `--text-base` (14px). Dense apps need density.
- No bold for body text. Bold only for: section headers, usernames,
  active states.
- Letter-spacing: 0.02em on all text. A bit of breathing room.
- Line-height: 1.6 for body text, 1.3 for headers.
- Text rendering: `text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;`

---

## Borders and Box-Drawing

This is the signature element. Unicode box-drawing characters for
structural borders instead of CSS border properties where it fits
visually.

### Box-drawing characters

```
+--            --+    Rounded corners for containers
|  content       |
+--            --+

+--            --+    Sharp corners for data/tables
|  content       |
+--            --+

-------------------    Horizontal separators between sections
```

Use real Unicode box-drawing characters in the implementation:
`-` (U+2500), `|` (U+2502), corners (U+256D-U+2570).

### When to use box-drawing vs CSS borders

| Element                    | Border style                                    |
|----------------------------|-------------------------------------------------|
| Cards, panels, containers  | CSS `border: 1px solid var(--border-default)`   |
| Section headers/labels     | Bracket label: `[ 0x10 VOICE ]`                |
| Message groups             | No border — spacing only                        |
| Input fields               | CSS border, accent on focus                     |
| Modals                     | CSS border + subtle shadow                      |
| Sidebar section separators | Box-drawing horizontal line                     |

### Bracket labels

Section identifiers and status badges use a bracket-label convention.
Two variants:

**Hex labels** — for section headers:
```
[ 0x10 CHATROOMS ]
[ 0x20 USERS ]
[ 0xFF SETTINGS ]
```
- The hex number is decorative, not functional. Assign aesthetically.
- ALL CAPS for label text.
- Colour: `--text-secondary` for brackets/hex, `--accent` for
  label text.
- Used for: sidebar section headers, settings sections,
  modal headers.

**Status labels** — for inline status indicators:
```
[CALL]  [MIC]  [CAM]  [LIVE]  [MUTED]
```
- ALL CAPS, no hex prefix.
- Colour: `--accent` for active states, `--text-muted` for inactive.
- Used for: call state, media state, connection state,
  mode indicators.
- The square bracket is the visual primitive for "the system speaks".

---

## Spacing system

8px base grid. All spacings are multiples of 8.

```css
:root {
  --space-1:  4px;    /* tight: between icon and label */
  --space-2:  8px;    /* default: padding inside compact elements */
  --space-3:  12px;   /* comfortable: padding inside cards */
  --space-4:  16px;   /* standard: gaps between elements */
  --space-6:  24px;   /* generous: section spacing */
  --space-8:  32px;   /* large: page-level sections */
}
```

### Density

Dense apps need compact spacing. No excessive padding.
- Messages: `--space-1` vertical gap between same-sender messages.
- Different sender: `--space-3` vertical gap.
- Sidebar items: `--space-2` vertical padding.
- Cards/panels: `--space-3` padding.

---

## Component patterns

### Buttons

```css
.btn-primary {
  background: transparent;
  color: var(--accent);
  border: 1px solid var(--accent);
  border-radius: 0;           /* NEVER round */
  padding: var(--space-2) var(--space-4);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: background 150ms, color 150ms;
}
.btn-primary:hover {
  background: var(--accent);
  color: var(--bg-base);
}
.btn-primary:focus-visible {
  box-shadow: var(--glow-ring);
  outline: none;
}
```

Rules:
- `border-radius: 0` on ALL interactive elements. No exceptions.
- Buttons are outlined by default, filled on hover. Inverted feel.
- Destructive buttons use `--error` instead of `--accent`.
- Disabled buttons: `--text-muted` colour, `--border-default` border,
  no hover effect.

### Input fields

```css
.input {
  background: var(--bg-input);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: 0;
  padding: var(--space-2) var(--space-3);
  font-family: var(--font-mono);
  font-size: var(--text-base);
}
.input:focus {
  border-color: var(--accent);
  box-shadow: var(--glow-ring);
  outline: none;
}
.input::placeholder {
  color: var(--text-muted);
}
```

### Range inputs (sliders)

```css
input[type="range"] {
  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: 0;
  outline: none;
}
input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  background: var(--accent);
  border: none;
  border-radius: 0;
  cursor: pointer;
}
input[type="range"]:focus-visible {
  box-shadow: var(--glow-ring);
}
```

### Status indicators

Three-tier hierarchy for state indicators:

| Tier | Size | Use | Example |
|------|------|-----|---------|
| Primary | 8px square | Online/offline, connection state | User online dot |
| Secondary | 6px square | Unread, notification count | Unread room indicator |
| Tertiary | 4px square | Minor state (muted, idle) | Muted mic indicator |

All indicators are squares (no circles), absolutely positioned
relative to the parent. Colour follows semantic tokens: `--success`
for positive, `--error` for negative, `--accent-muted` for
neutral/inactive.

### Chat messages

- No bubbles. Messages are flat text blocks on `--bg-base`.
- Username: `--accent` colour, font-weight 500.
- Timestamp: `--text-muted`, `--text-xs` size, inline after the username.
- Message text: `--text-primary`.
- Message groups: same sender within 5 minutes is grouped, the
  username is shown once.

### Sidebar

- Width: 240px default, collapsible.
- Background: `--bg-surface`.
- Section headers: hex-label format.
- Active item: `--bg-elevated` background, `--accent` left border (2px).
- Hover: `--bg-elevated` background.
- Unread indicator: `--accent` dot (6px square) to the left of the
  item name.

### Modals and overlays

**Layer map** — consistent z-index architecture:

| Layer | Z-index | Use |
|-------|---------|-----|
| Base content | 0 | Normal page content |
| Sticky elements | 10 | Sticky headers, floating bars |
| Sidebar overlay (mobile) | 40-50 | Mobile sidebar drawer |
| Backdrop | 49 | Semi-transparent overlay behind modals/drawers |
| Dropdown/context menu | 50-60 | Popover menus, right-click menus |
| Modal | 70-80 | Dialog windows |
| Toast/banner | 90-100 | Notifications, connection banners |

**Modal styling:**
- Background: `--bg-elevated`.
- Border: `1px solid var(--border-default)`.
- No border-radius.
- Backdrop: `rgba(10, 10, 20, 0.7)` with `backdrop-filter: blur(4px)`.
- Header: bracket-label format.
- Shadow: `box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);` — modals only.
- Centring: `position: fixed; top: 50%; left: 50%;
  transform: translate(-50%, -50%);`

**Dismiss patterns** (all three mandatory for modals):
- Escape key closes
- Click outside closes
- An explicit close button (X) is present

**Context menus / dropdowns:**
- Use portal rendering (e.g., `createPortal`) to avoid overflow
  clipping.
- Same visual rules as modals (`--bg-elevated`, border, no radius).

### Scrollbars

```css
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--border-default); }
::-webkit-scrollbar-thumb:hover { background: var(--accent-muted); }
```

---

## Animation and transitions

Two categories. Don't mix.

### Transitions (state changes)

- Duration: 150ms for colours/borders, 200ms for transforms/opacity.
- Easing: `ease-out` for entrances, `ease-in` for exits.
- Apply to: hover, focus, active, open/close, expand/collapse.
- Cursor: default. No custom cursors.

### Keyframe animations (continuous feedback)

Sparingly allowed for activity indicators:

```css
@keyframes speaking-pulse {
  0%   { box-shadow: 0 0 0 2px var(--glow-speaking),
                     0 0 8px rgba(168, 216, 185, 0.3); }
  50%  { box-shadow: 0 0 0 4px var(--glow-speaking),
                     0 0 16px rgba(168, 216, 185, 0.5); }
  100% { box-shadow: 0 0 0 2px var(--glow-speaking),
                     0 0 8px rgba(168, 216, 185, 0.3); }
}

@keyframes fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
```

- `speaking-pulse`: 1s ease-in-out infinite. For active user/element
  glow.
- `fade-in`: for banners, toasts, modal entrance.
- NO gratuitous animations. No page-load animations. No bounce
  effects.
- A loading spinner is OK if it conveys progress/activity. The text
  `loading...` or a blinking cursor `_` is also fine — choose per
  context. Prefer real progress (`3/10`, `42%`) when measurable.

---

## Layout rules

- No rounded corners anywhere. `border-radius: 0` is a hard rule.
  Exception: 2px max on avatar/image edges to soften pixel aliasing.
- No drop shadows except on modals and dropdowns.
- No gradients on surfaces. Flat colour only.
- No blur effects on surfaces (modal backdrop only).
- Icons are OK when they support readability (action buttons, status,
  navigation). Use a consistent style (e.g., Lucide stroke icons) and
  a neutral size (16-20px). Prefer paired icon+label; icon-only only
  when the action is unambiguous (close, settings, media controls).
  Emoji as a functional icon is out — use SVG.

---

## Accessibility

### Focus management

- All interactive elements MUST have `:focus-visible` styles with
  `box-shadow: var(--glow-ring); outline: none;`
- Keyboard navigation must work for every interaction.
- Escape closes modals, menus, overlays.
- Enter submits forms, activates buttons.

### Contrast

- `--text-primary` on `--bg-base` = ~9.5:1 (excellent)
- `--accent` on `--bg-base` = ~7.5:1 (excellent)
- `--text-secondary` on `--bg-base` = ~4.2:1 (acceptable for metadata,
  not body text — never use `--text-secondary` for primary content)
- Minimum: 4.5:1 for body text, 3:1 for large text (WCAG AA).

### ARIA and semantics

- ARIA labels on all icon-only buttons (`aria-label`).
- Semantic roles on custom widgets (`role="menu"`, `role="menuitem"`,
  `role="dialog"`).
- Correct button types (`type="button"` on non-submit buttons).
- Sensible heading hierarchy (h1 > h2 > h3, no skipping).

### Touch targets

- Minimum tap target: 44x44px on mobile (interactive sidebar items,
  buttons, links).
- Desktop can use smaller targets (32px min) due to pointer
  precision.

---

## Responsive behaviour

Desktop-first. Primary target: 1280px+ screens.

### Breakpoints

| Range | Label | Layout |
|-------|-------|--------|
| 1280px+ | Desktop | Sidebar visible, full layout |
| 768-1279px | Tablet | Sidebar collapses to icons-only, expandable |
| < 768px | Mobile | Sidebar as overlay drawer, content full-width |

### Mobile sidebar drawer

```css
/* Sidebar slides in from left */
.sidebar {
  position: fixed;
  top: 0; left: 0; bottom: 0;
  width: 280px;
  z-index: 50;
  transform: translateX(-100%);
  transition: transform 200ms ease;
}
.sidebar.open {
  transform: translateX(0);
}

/* Backdrop behind drawer */
.sidebar-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(10, 10, 20, 0.5);
  z-index: 49;
}
```

### Grid behaviour

The monospace grid does not break — it shrinks character by
character. Pattern: `owickstrom/the-monospace-web`.

---

## Domain extension points

Projects using this skill may need domain-specific tokens beyond the
global palette. Define them as additional CSS custom properties:

```css
:root {
  /* Domain-specific extensions */
  --chat-font-size: 0.875rem;      /* chat apps */
  --video-aspect: 16 / 9;          /* media apps */
  --sidebar-width: 240px;          /* configurable sidebar */
}
```

Rules for extensions:
- Prefix with the domain context (`--chat-*`, `--video-*`, `--call-*`).
- NEVER override global tokens — extend alongside them.
- Document extensions in the project `theme.css`, not here.

---

## Red flags

Observable signals that the skill is being violated or applied
poorly — for self-monitoring and code review:

- Hardcoded `#hex` values in components instead of CSS vars
- `border-radius: 4px` (or more) anywhere — only 0 or up to 2px is
  allowed
- `font-family: sans-serif` / `system-ui` without a `--font-mono`
  fallback chain
- `box-shadow` on cards/panels (non-modal surfaces)
- Chat bubbles in Discord/WhatsApp style
- `linear-gradient(...)` on backgrounds
- Material/Tailwind default components without adaptation
- `color: #fff` or `background: #000` (pure white/black)
- Emoji as a functional icon (e.g., a submit button with "rocket
  emoji")
- Toast notifications with rounded corners + drop shadow
- Custom cursor (`cursor: url(...)`)
- Tree-prefix characters in navigation (`├─`, `└─`) — box drawing for
  borders yes, but not as a bullet replacement
- Animation spam (hover bounce, page-load stagger, gratuitous
  transitions)
- A theme block that overrides only part of the token palette (it
  should always redefine ALL tokens)

## Anti-patterns (NEVER do this)

- `border-radius > 2px` (rounded corners)
- Drop shadows on cards or panels (modals/dropdowns only)
- Gradient backgrounds on surfaces
- Chat bubbles (Discord/WhatsApp style)
- Proportional fonts anywhere
- Bold/saturated colours without desaturation (no pure red/blue/green)
- Generic Material Design or Tailwind default components
- Toast notifications with rounded corners and shadows
- Emoji as a functional icon (use text labels or SVG icons)
- Fake progress with no signal (e.g., infinite shimmer on a panel
  that never updates). Spinners/indicators must reflect real
  activity.
- White or light backgrounds on any element
- Tree-prefix characters in navigation
- Hardcoded hex values in components (use CSS vars)
- Custom cursors

## Common rationalisations

| Rationalisation | Reality |
|---|---|
| "Just a tiny radius on the card corner, won't hurt" | Exactly these inconsistencies make the AI-aesthetic look. Hard rule = 0 or 2px max. |
| "One hex value directly in a component is OK, just this once" | Theming breaks. The first theme variant uncovers the blind spot — usually weeks later. |
| "Chat bubbles are better for UX" | The Discord/Slack/WhatsApp convergence argument. TTY aesthetic is explicitly different — anyone wanting that uses a different skill. |
| "An npm Material component will do, I'll customise later" | "Later" doesn't happen. The component carries foreign visual defaults through the entire app. |
| "Pure black `#000` is darker, so better for a dark theme" | Pure black creates halo effects and lacks contrast against the underlying system UI. `--bg-input` (`#16162a`) is the lower bound. |
| "A drop shadow makes cards prettier" | Makes them look like a Material card lookalike. TTY has 4 background layers for depth — shadow is a modal-only signal. |

## Contract

### INPUT

- Required: a project with a web UI (HTML/CSS or a framework like
  React/Vue/Svelte) that wants to adopt or already uses TTY aesthetic.
- Optional: existing theme file to extend, or a component library to
  check for conformance.
- Context: the project intent / decisions file should declare TTY
  style explicitly as the default.

### OUTPUT

- DELIVERS: concrete CSS custom properties (colour, type, spacing,
  border), component pattern snippets (button, input, modal, sidebar,
  status indicator, chat message), layer map (z-index), animation
  patterns, anti-pattern list.
- DOES NOT DELIVER: generic UI methodology (component architecture,
  state management, test patterns) — that is `frontend_ui_engineering`.
  Also no UX heuristics (Nielsen, IA, interaction) — that is
  `spec_board mode=ux`.
- ENABLES: consistent TTY aesthetic across multiple
  components/pages, theme variants without refactoring, code review
  against a clear pattern list.

### DONE

- [ ] A `:root` token block exists in the project with all mandatory
      tokens (colour, type, spacing, border).
- [ ] Components reference CSS vars exclusively, no hardcoded hex
      values.
- [ ] Walked through the anti-pattern list — no hits.
- [ ] In a multi-theme setup: every theme redefines the COMPLETE
      token palette (no partial override).

### FAIL

- Retry: fix individual anti-pattern hits (replace hardcoded hex,
  set border-radius to 0, etc.). No skill escalation.
- Escalate: on systemic incompatibility (e.g., the app uses a
  component library that does not allow TTY tokens) — decision to the
  user: switch library, wrap library, or drop TTY aesthetic for this
  sub-app.
- Abort: if the project explicitly declares a different aesthetic
  (Material, Glassmorphism, etc.) — the TTY skill is wrong here, use
  another design discipline.
