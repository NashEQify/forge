---
name: frontend-ui-engineering
description: >
  Production-quality UI discipline. Component architecture, state decisions,
  design-system adherence (no AI aesthetic), a11y (WCAG 2.1 AA), responsive,
  meaningful empty/loading/error states. Code-side methodology paired with
  spec_board mode=ux (spec side) and code_review_board (diff side).
status: active
invocation:
  primary: workflow-step
  secondary: [user-facing]
disable-model-invocation: false
uses: []
---

# Skill: frontend-ui-engineering

## Source

Upstream: [frontend-ui-engineering/SKILL.md](https://github.com/addyosmani/agent-skills/blob/main/skills/frontend-ui-engineering/SKILL.md) (MIT, Copyright Addy Osmani 2025). Content adapted for forge: standard skill format, cross-refs to `spec_board mode=ux` (spec side) and `code_review_board` (code side), connection to `references/accessibility-checklist.md` + `references/performance-checklist.md`. Example snippets remain React/Tailwind-centred — patterns are framework-agnostic, snippets are illustrative.

## Purpose

**Build production-quality UI** that does not look AI-generated. That means: real design-system adherence, proper accessibility, considered interaction patterns, and no generic "AI aesthetic" (purple gradients, oversized cards, stock layouts).

This skill is **code-side methodology**. It complements:
- `spec_board mode=ux` — UX review of spec artefacts (spec side)
- `code_review_board` — code-diff review (diff side)

The skill is the running build instruction in between: what must be done **during** building so that what the spec side intended and what the diff side reviews come together.

## When to use

- Building new UI components / pages
- Changing existing user-facing interfaces
- Implementing responsive layouts
- Adding interactivity / state management
- Fixing visual / UX issues

### Do not invoke for

- UX spec review (reader-facing surface) -> `spec_board mode=ux`
- Code review of a frontend diff -> `code_review_board` (with UX specialist personas)
- Backend API design -> `api_and_interface_design`
- One-shot a11y audit -> `references/accessibility-checklist.md` + axe-core / pa11y / Lighthouse directly
- Performance tuning of an existing app -> separate discipline (`references/performance-checklist.md` + profiler)

## Standalone rationale

Why a separate skill rather than a mode of `code_review_board` or
`spec_board mode=ux`?

- **`spec_board mode=ux`** = spec-side review of UX artefacts (3 UX
  personas: Heuristic / IA / Interaction). A reviewer pass over the spec, not
  build instructions while code is being written.
- **`code_review_board`** = diff-side review after building. A reviewer pass
  with findings output. UX specialist personas there can load this skill as
  their methodology anchor.
- **`frontend_ui_engineering` (this skill)** = the running build
  discipline **in between**: what must happen during building so that
  spec-side intent (mode=ux) and code-side reviewability (code_review_board)
  come together. Component architecture, state decisions, design-system
  adherence, a11y in code, the 4 states.

Deleting it and integrating it into `code_review_board` as a mode would tie
the discipline to diff reviews — but frontend methodology applies **during
the build** (component file layout, container/presentation split, state-tree
decisions), not just retrospectively in review. Standalone rationale:
methodology container for the build phase, consumed by boards on both sides.

## Component architecture

### File structure (colocate)

Component logic, tests, styles and hooks together:

```
src/components/
  TaskList/
    TaskList.tsx          # component implementation
    TaskList.test.tsx     # tests
    TaskList.stories.tsx  # Storybook stories (when used)
    use-task-list.ts      # custom hook (when state is complex)
    types.ts              # component-specific types (when needed)
```

**Custom-hook example** (`use-task-list.ts`):

```tsx
// Encapsulates state + handlers, isolates them from rendering.
// Component file consumes: const { tasks, toggle, remove } = useTaskList();
// Test file mocks: jest.mock('./use-task-list'); useTaskList.mockReturnValue({...});
import { useState, useCallback } from 'react';
import type { Task } from './types';

export function useTaskList(initial: Task[] = []) {
  const [tasks, setTasks] = useState<Task[]>(initial);

  const toggle = useCallback((id: string) => {
    setTasks(ts => ts.map(t => t.id === id ? { ...t, done: !t.done } : t));
  }, []);

  const remove = useCallback((id: string) => {
    setTasks(ts => ts.filter(t => t.id !== id));
  }, []);

  return { tasks, toggle, remove };
}
```

Trigger for a custom hook: component > 100 lines with nested state logic, or
the same state logic duplicated across 2+ components.

### Composition over configuration

```tsx
// GOOD — composable
<Card>
  <CardHeader>
    <CardTitle>Tasks</CardTitle>
  </CardHeader>
  <CardBody>
    <TaskList tasks={tasks} />
  </CardBody>
</Card>

// AVOID — over-configured (every variation = a new prop)
<Card
  title="Tasks"
  headerVariant="large"
  bodyPadding="md"
  content={<TaskList tasks={tasks} />}
/>
```

### Container vs presentation

```tsx
// Container — handles data + lifecycle
export function TaskListContainer() {
  const { tasks, isLoading, error, refetch } = useTasks();
  if (isLoading) return <TaskListSkeleton />;
  if (error) return <ErrorState message="Failed to load tasks" retry={refetch} />;
  if (tasks.length === 0) return <EmptyState message="No tasks yet" />;
  return <TaskList tasks={tasks} />;
}

// Presentation — pure rendering
export function TaskList({ tasks }: { tasks: Task[] }) {
  return (
    <ul role="list" className="divide-y">
      {tasks.map(task => <TaskItem key={task.id} task={task} />)}
    </ul>
  );
}
```

Rationale: tests for presentation = snapshot or simple render assert. Tests
for container = mock data + lifecycle. Mixed = unmockable.

## State management decision tree

**Choose the simplest approach that works:**

```
Local state (useState)            -> component-specific UI state
Lifted state                      -> shared between 2-3 sibling components
Context                           -> theme / auth / locale (read-heavy, write-rare)
URL state (searchParams)          -> filter / pagination / shareable UI state
Server state (React Query / SWR)  -> remote data with caching
Global store (Zustand / Redux)    -> complex client state shared app-wide
```

**Avoid prop drilling deeper than 3 levels.** When props pass through
non-consuming components -> use Context or restructure the component tree.

## Design-system adherence

### Avoid the AI aesthetic

AI-generated UI has recognisable patterns. Avoid all of:

| AI default | Why it's a problem | Production quality |
|---|---|---|
| Purple/indigo everywhere | Models default to "safe" colours, every app looks the same | The project's actual colour palette |
| Excessive gradients | Visual noise, clashes with most design systems | Flat or subtle, aligned with the design system |
| `rounded-2xl` everywhere | Maximum rounding signals "friendly" but ignores hierarchy | Consistent border-radius per component class |
| Generic hero sections | Template-driven, no relation to actual content / user need | Content-first layouts |
| Lorem-ipsum-style copy | Placeholder text hides layout problems that real content surfaces | Realistic placeholder content |
| Oversized padding everywhere | Equally generous padding destroys visual hierarchy | Consistent spacing scale |
| Stock card grids | Uniform grids ignore information priority | Purpose-driven layouts |
| Shadow-heavy design | Layered shadows cost render time + compete with content | Subtle / no shadow unless the design system specifies it |

### Spacing scale + typography + colour

Spacing: consistent scale, no arbitrary pixel values:

```css
/* GOOD — scale (Tailwind or your own 0.25rem steps) */
padding: 1rem;       /* 16px */
gap: 0.75rem;        /* 12px */

/* BAD — off-scale */
padding: 13px;
margin-top: 2.3rem;
```

Typography: respect the type hierarchy — `h1 > h2 > h3 > body > small`. Do
not skip heading levels, do not use heading styles for non-heading content.

Colour: semantic tokens (`text-primary`, `bg-surface`, `border-default`),
not raw hex. Contrast 4.5:1 for normal text, 3:1 for large text (WCAG AA).
Colour **never** as the sole indicator (pair with icons / text / patterns).

## Accessibility (WCAG 2.1 AA)

Cross-ref: `references/accessibility-checklist.md` for detailed mandatory
checks. Here, the pattern discipline:

### Keyboard navigation

```tsx
// GOOD — native button, focusable by default
<button onClick={handleClick}>Click me</button>

// BAD — div as click target, not focusable
<div onClick={handleClick}>Click me</div>

// OK but ONLY when <button> is genuinely impossible
<div role="button" tabIndex={0} onClick={handleClick}
     onKeyDown={e => {
       if (e.key === 'Enter') handleClick();
       if (e.key === ' ') e.preventDefault();
     }}
     onKeyUp={e => { if (e.key === ' ') handleClick(); }}>
  Click me
</div>
```

### ARIA labels

```tsx
<button aria-label="Close dialog"><XIcon /></button>

<label htmlFor="email">Email</label>
<input id="email" type="email" />

<input aria-label="Search tasks" type="search" />
```

### Focus management

**`<dialog open>` is NOT modal** — no focus trap, no inert background,
no escape close, no backdrop. A real modal requires
`dialogElement.showModal()` (DOM API) plus focus restoration on close.

```tsx
function Dialog({ isOpen, onClose, triggerRef }: DialogProps & { triggerRef: RefObject<HTMLElement> }) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    if (isOpen && !el.open) {
      el.showModal();              // modal: focus trap, inert background, ESC close, backdrop
    } else if (!isOpen && el.open) {
      el.close();
      triggerRef.current?.focus(); // focus restore to the trigger element
    }
  }, [isOpen, triggerRef]);

  return (
    <dialog ref={dialogRef} onClose={onClose}>
      {/* form method="dialog" -> submit button closes the dialog without JS */}
      <form method="dialog">
        <button>Close</button>
      </form>
      {/* dialog content */}
    </dialog>
  );
}
```

**iOS polyfill:** `<dialog>` is natively supported only from iOS 15.4. Older:
load the `dialog-polyfill` package and call
`polyfill.registerDialog(dialogRef.current)` once in useEffect.

**Mandatory a11y combination:** `showModal()` (focus trap) + `triggerRef.focus()`
on close (focus restore) + `<form method="dialog">` (escape/submit close)
together deliver WCAG-compliant modal semantics. `<dialog open>` alone does
**not**.

### Empty / loading / error states

Don't show blank screens. Every dynamic list has 4 states: loading, empty,
error, populated.

```tsx
function TaskList({ tasks }: { tasks: Task[] }) {
  if (tasks.length === 0) {
    // role="status" is correct here because the empty-state region appears
    // as the result of a data-loading process (initial render with empty
    // array, or after a filter reset). Screen readers announce the
    // populated -> empty transition. For a TRULY static empty state
    // (page renders from the start with an empty list, no loading before):
    // omit the role and let it be plain content.
    return (
      <div role="status" className="text-center py-12">
        <TasksEmptyIcon className="mx-auto h-12 w-12 text-muted" />
        <h3 className="mt-2 text-sm font-medium">No tasks</h3>
        <p className="mt-1 text-sm text-muted">Get started by creating a task.</p>
        <Button className="mt-4" onClick={onCreateTask}>Create Task</Button>
      </div>
    );
  }
  return <ul role="list">{/* ... */}</ul>;
}
```

## Responsive design

Mobile-first. Test at: 320px, 768px, 1024px, 1440px.

```tsx
<div className="
  grid grid-cols-1
  sm:grid-cols-2
  lg:grid-cols-3
  gap-4
">
```

## Loading + transitions

Skeleton loading instead of spinners for content (perceived speed):

```tsx
function TaskListSkeleton() {
  // ARIA pattern: aria-busy + aria-label on the parent container,
  // role="status" + aria-live=polite so screen readers announce the
  // loading transition. The individual skeleton bars carry no ARIA —
  // they are decorative children under aria-busy=true.
  return (
    <div role="status" aria-busy="true" aria-live="polite" aria-label="Loading tasks" className="space-y-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="h-12 bg-muted animate-pulse rounded" aria-hidden="true" />
      ))}
      <span className="sr-only">Loading tasks</span>
    </div>
  );
}
```

Optimistic updates for perceived speed on mutations — with error recovery,
rollback toast + onSettled refresh, plus race-condition protection:

```tsx
function useToggleTask() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();  // your toast system

  return useMutation({
    mutationFn: toggleTask,

    onMutate: async (taskId) => {
      // 1. Cancel in-flight refetches so our optimistic update is not
      //    overwritten by a staler server response
      await queryClient.cancelQueries({ queryKey: ['tasks'] });

      // 2. Capture previous state for rollback
      const previous = queryClient.getQueryData<Task[]>(['tasks']);

      // 3. Optimistic update
      queryClient.setQueryData<Task[]>(['tasks'], (old = []) =>
        old.map(t => t.id === taskId ? { ...t, done: !t.done } : t)
      );

      return { previous };
    },

    onError: (err, _id, ctx) => {
      // Rollback + toast: a silent rollback confuses the user
      // ("I clicked but nothing happened").
      if (ctx?.previous) queryClient.setQueryData(['tasks'], ctx.previous);
      showToast({ kind: 'error', message: 'Toggle failed', detail: err.message });
    },

    onSettled: () => {
      // Race-condition protection: parallel mutations can overwrite one
      // another. onSettled invalidates the cache after EVERY mutation
      // (success or error) -> the server is the truth.
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}
```

**Hook contract hint:** `useTasks()` and similar query hooks return
*either* `tasks: Task[]` (always an array, possibly empty) OR `tasks: Task[]
| undefined` (undefined before the first fetch). **Standardise per repo** —
mixing the two creates cherry-pick risk (`tasks?.length` defensive,
`tasks.length` direct). Recommendation: hook returns `tasks: undefined`
when `isLoading=true`, `tasks: Task[]` when `isSuccess=true` (even if
empty). A TypeScript discriminated union makes this explicit.

## Performance

Cross-ref: `references/performance-checklist.md`.

Core pattern: don't load everything up front. Code splitting for routes /
heavy components. Image optimisation (next/image, srcset, lazy loading).
Avoid layout shift (CLS) via fixed dimensions on images / skeletons.

## Red flags

- Components > 200 lines (split)
- Inline styles or arbitrary px values
- Missing empty / loading / error states
- No keyboard test performed
- Colour as sole indicator
- Generic AI look in production UI
- `<dialog open>` without `showModal()` (non-modal, no focus trap)
- Optimistic updates without onError rollback + onSettled refresh

## Common rationalisations

| Rationalisation | Reality |
|---|---|
| "Accessibility is nice-to-have" | Legal requirement in many jurisdictions + an engineering quality standard |
| "We'll do responsive later" | Retrofitting is 3x more expensive than building it from scratch |
| "Design isn't final yet, no styling" | Use design-system defaults — unstyled UI = broken first impression |
| "It's just a prototype" | Prototypes ship to production. Build the foundation properly. |
| "AI aesthetic is OK for now" | Signals low quality. The project's design system from day 1. |

## Contract

### INPUT

- **Required:** UI component / page / layout spec or an existing UI diff
- **Optional:** design-system reference (Storybook / Figma / tokens file), brand colours, spacing scale
- **Context:** repo component conventions (`src/components/` layout), style system (Tailwind / CSS Modules / styled-components), `references/accessibility-checklist.md`, `references/performance-checklist.md`

### OUTPUT

**DELIVERS:**
- Component implementation with colocated tests + stories (when Storybook is used)
- A11y-compliant (WCAG 2.1 AA) UI with all 4 states (loading/empty/error/populated)
- Responsive layout (mobile-first, breakpoint-tested)
- Design-system-compliant spacing/typography/colour (no off-scale values, no AI aesthetic)

**DOES NOT DELIVER:**
- **No UX spec review** -> `spec_board mode=ux`
- **No code review** -> `code_review_board` (the frontend diff goes through the board, not this skill)
- **No a11y audit tool run as a mandatory verify gate** -> dedicated tooling (axe-core, pa11y, Lighthouse) provides that. A dev-time spot check during the build (axe-core devtools extension manually or jest-axe in unit tests) is part of the discipline and referenced in DONE — that is not a full audit, it is a smoke test during implementation.
- **No performance profiling of an existing app** -> profiler tooling + `references/performance-checklist.md`
- **No design-system authoring** (token definition, colour-palette selection) -> outside the skill's scope

**ENABLES:**
- Build-workflow verify phase: the frontend diff passes through `code_review_board` with UX specialist personas that use this skill as their methodology anchor
- spec_board mode=ux: a UX spec references this skill as the "how is this implemented" reference
- shipping_and_launch: the pre-launch checklist has a11y state coverage as an item

### DONE

- 4 states covered (loading, empty, error, populated) with `role="status"` / `aria-busy` / etc.
- Keyboard navigation works (Tab through the page, no click trap)
- ARIA labels on icon-only buttons / form inputs without a visible label
- Spacing/typography/colour from the design system (no arbitrary px / hex)
- Responsive tested at 320 / 768 / 1024 / 1440 px
- Empty / error / loading states have meaningful content (no blank screen)
- Console has 0 errors / 0 a11y warnings (axe-core in dev)

### FAIL

- **Retry:** a11y tool warnings -> component edit, re-test
- **Escalate:** design-system conflict (spec demands off-scale spacing or a new colour) -> spec_board mode=ux or Council
- **Abort:** not provided — UI build continues, findings are surfaced

## Boundary

- **Reviews (spec side / code side):** `spec_board mode=ux` + `code_review_board`. This skill provides the methodology that the boards review.
- **Other methodology layers:** `api_and_interface_design` (backend boundary), `security_and_hardening` (auth/input/secrets).
- **Tooling, not a skill:** axe-core / Lighthouse (a11y audit run), Storybook (component workshop), Figma/Tokens Studio (design-token authoring).

## Anti-patterns

- **DO NOT** use `<div onClick=...>` (with or without `role="button"`) as a click target. **INSTEAD** use `<button>` — natively keyboard-focusable + screen-reader affordance + Enter/Space behaviour. If `<button>` does not work for layout reasons: `role="button" tabIndex={0}` PLUS keyboard handler for Enter/Space (without it, `role` is a broken promise).
- **DO NOT** use colour as the sole state indicator (e.g., red border = error). **INSTEAD** icon + text + colour. Why: colour-blind users + reader modes lose the signal.
- **DO NOT** skip heading levels (`h1 -> h3`). **INSTEAD** real hierarchy. Why: screen readers use headings for navigation, skipping = disorientation.
- **DO NOT** ship images without `alt`. **INSTEAD** descriptive alt or `alt=""` if decorative. Why: blank alt = the screen reader reads the filename.
- **DO NOT** auto-play video / animated auto-carousels without pause. **INSTEAD** user control or respect `prefers-reduced-motion`. Why: vestibular disorders, ADHD, plus respect for user attention.
- **DO NOT** return `null` for an empty state. **INSTEAD** a meaningful empty message + action. Why: blank screen = unclear whether loading, error, or empty.
- **DO NOT** prop-drill >3 levels. **INSTEAD** Context or restructure the component tree. Why: every intermediate level must carry the props through, refactoring becomes painful.
- **DO NOT** use AI aesthetic (purple gradients, oversized cards, stock layouts). **INSTEAD** the project's actual design system. Why: signals "low effort", erodes trust + brand.
- **DO NOT** keep components > 200 lines with nested branch logic. **INSTEAD** split container/presentation + custom hook (`use-<name>.ts`) for state + sub-components. Why: monolithic components are unmockable, untestable, refactor-resistant. Red-flag counterpart.

## References

| Topic | SoT |
|-------|-----|
| Spec-side UX review | `skills/spec_board/SKILL.md` (mode=ux: 3 UX personas) |
| Code-side diff review | `skills/code_review_board/SKILL.md` (UX specialists load this skill) |
| A11y detail checklist | `references/accessibility-checklist.md` |
| Performance detail checklist | `references/performance-checklist.md` |
| Pre-launch | `skills/shipping_and_launch/SKILL.md` |
| Cross-boundary with backend | `skills/api_and_interface_design/SKILL.md` |
