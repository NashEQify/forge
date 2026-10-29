# Frontend UI engineering — component structure and styling

Step-loaded unit of `skills/frontend_ui_engineering/SKILL.md`. Read it when laying out a component's files, splitting
container from presentation, choosing where state lives, and when applying spacing, typography and colour.

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
