# Frontend UI engineering — accessibility, responsive and UI states

Step-loaded unit of `skills/frontend_ui_engineering/SKILL.md`. Read it when implementing interaction, focus, dialogs
or ARIA, the loading / empty / error / populated states, transitions and optimistic updates, responsive layout, and
when loading heavy routes, components or images.

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
