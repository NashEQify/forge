# Frontend design TTY — design tokens

Step-loaded unit of `skills/frontend_design_tty/SKILL.md`. Read it when setting up or extending a project's token
block (Process step 1), when selecting a colour, type, spacing or border value, and when setting up a theme variant.

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
