# Visual guide — capabilities and workflows

These diagrams explain the operating shape. Canonical method contracts and runbooks
define the actual steps, gates and completion requirements. Not every request starts
a software workflow.

## Choose the relevant capability

```mermaid
flowchart TD
    A[Describe the result and constraints] --> B{What does the work need?}
    B --> K[Knowledge and continuity]
    B --> R[General reasoning]
    B --> D[Selected software development]
    K --> KR[Retrieve, reconcile and continue]
    R --> RR[Clarify, examine or compare]
    D --> DR[Specify, implement and verify]
    KR --> O[Useful result with evidence and limits]
    RR --> O
    DR --> O
```

The capabilities compose: a decision can use stored knowledge, and a development
workflow can invoke a reasoning method. The [capability contract](../framework/capabilities.md)
owns the boundaries. Profile selection controls availability, not workflow selection.

## Knowledge and continuity

```mermaid
flowchart TD
    A[Question or useful new information] --> B[Find the authorized owner]
    B --> C[Capture coherent context and check recovery]
    C --> D{Pending reconciliation?}
    D -->|Yes| E[Inspect actual files and reconcile]
    E --> F[Reason from current evidence]
    D -->|No| F
    F --> G{Knowledge changed?}
    G -->|No| H[Use it without redundant writes]
    G -->|Yes| I[Reconcile owner and affected routes]
    I --> J[Publish against the protected baseline]
    J --> K{Baseline still current?}
    K -->|No| C
    K -->|Yes| L[Verify outcome and report limits]
```

Personal and project scopes remain separate. Pending recovery must be resolved or
the dependent result qualified. Read the [Knowledge Processor](../skills/knowledge_processor/SKILL.md)
and [protected publication contract](../framework/continuity.md) for exact semantics.

### Save and resume

```mermaid
flowchart LR
    A[Useful changes during work] --> B[Reconcile knowledge]
    B --> C[Update open-topic handoff]
    D[Selected development contribution] -. when selected .-> C
    C --> E[Protected publication]
    E --> F[Authorized commit and push]
    F --> G[Report actual persistence]
    G --> H[Later session reads and validates]
```

An explicit `save` requests active-project upstream commit/push unless local rules
restrict it. Ordinary continuous maintenance alone does not. Without Git, save can
still preserve local continuity. A partial publication or missing selected domain
contribution stays visible; the diagram's arrows are not success evidence.
[Save runbook](../workflows/runbooks/save/WORKFLOW.md).

## General reasoning

```mermaid
flowchart TD
    A[Problem, constraints and available evidence] --> B{Where is the uncertainty?}
    B -->|Problem shape| F[Frame]
    B -->|Underlying assumption| D[Bedrock]
    B -->|Choice between alternatives| C[Council]
    F --> FO[Reformulated problem and solution space]
    D --> DO[Assumptions, values and implications]
    C --> CO[Positions, trade-offs and recommendation]
    FO --> R[Usable inline report with uncertainty]
    DO --> R
    CO --> R
    R --> U[User-owned decisions remain explicit]
    R -. authorized persistence .-> P[Knowledge owner or caller artifact]
```

Supplied context is sufficient. No repository, software task or engine record is
required. Independent Council modes collect member investigations before Chief
consolidation and Buddy's source checks. Interactive Council uses moderated dialogue.
[Frame](../skills/frame/SKILL.md) · [Bedrock](../skills/bedrock_drill/SKILL.md) · [Council](../skills/council/SKILL.md).

## Software development

Development is selected by project intent or explicit invocation. On-demand projects
retain their own working rules; old task files or installed tooling do not select
software automatically. [Process map](../framework/process-map.md#workflow-selection).

```mermaid
flowchart TD
    A[Selected software outcome] --> B{What is needed?}
    B -->|Defined feature| C[Build]
    B -->|Defect| D[Fix]
    B -->|Existing spec validation| E[Review]
    B -->|Knowledge gap| F[Research]
    B -->|Open solution shape| G[Solve]
    B -->|Reader-facing rewrite| H[Docs-Rewrite]
    C --> I[Appropriate checks and closeout]
    D --> I
    E --> I
    F --> I
    G --> I
    H --> I
    I --> J[Selected state contributes to continuity]
```

### Build and fix

```mermaid
flowchart LR
    A[Authorized feature] --> B[Select proportional Build path]
    B --> C[Establish required contract and preparation]
    C --> D[Implement]
    D --> E[Verify behavior and review]
    E --> F[Close selected obligations]
```

Eligible DIRECT work uses a short complete lifecycle rather than every preparation
gate. Larger or consequential changes retain their selected path's safeguards.
The [Build runbook](../workflows/runbooks/build/WORKFLOW.md) and runtime route definition
own the detailed sequence.

```mermaid
flowchart TD
    A[Defect or incident] --> B{Ongoing harm?}
    B -->|Yes| C[Authorized bounded recovery]
    C --> D[Verify service and user outcome]
    D --> E[Record restored state and remaining uncertainty]
    B -->|No| F[Investigate cause]
    E --> F
    F --> G[Verify cause and define regression evidence]
    G --> H[Authorized permanent repair]
    H --> I[Verify and close selected obligations]
```

Recovery preserves authorization boundaries and distinguishes restored service from
a resolved cause. [Fix runbook](../workflows/runbooks/fix/WORKFLOW.md).

## State is evidence, not automatic execution

A saved continuation points to exact selected development state. Restore validates
it without advancing or unpausing work. Workflow summaries do not replace the full
state, and gitignored state does not move automatically through Git.

Housekeeping follows the common knowledge lifecycle. An upgrade follows coordinated
installation and fresh verification. Neither needs to invent a software workflow
for ordinary knowledge use.

[Usage and methods](06-usage-workflows.md) · [Daily handbook](13-operational-handbook.md) ·
[Architecture](02-architecture.md) · [Documentation hub](README.md)
