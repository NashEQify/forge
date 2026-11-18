# Frontend design TTY — component patterns

Step-loaded unit of `skills/frontend_design_tty/SKILL.md`. Read it when picking a component pattern for a component
or layout (Process step 2), when adding motion, focus, contrast, ARIA or responsive behaviour, and when adding
domain-specific tokens (Process step 4).

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
