# BeFluent editorial UI implementation plan

**Goal:** Implement the approved editorial learning studio blueprint in the existing application.
**Architecture:** Keep existing Next.js routes, API contracts and learning engine. Shared tokens and shell establish the visual language; task-specific screens preserve real data and explicit empty/error states.
**Stack:** Next.js / React / Tailwind / Lucide / FastAPI; no provider changes.
**Spec:** Approved blueprint in this task: Today → session → completion, four primary navigation destinations, editorial typography, truthful progress, responsive UI.

## Constraints
- No commits, staging, deployment, destructive commands or file deletions.
- Interface in Portuguese; en, es-ES, fr, ja, zh-CN retained.
- Preserve authentication, infrastructure and AI provider configuration.
- Work in the user-selected checkout; leave reviewable uncommitted changes.
- No fabricated fluency percentages or charts inferred from truncated history.

## Tasks and ownership
- [ ] Foundation: globals.css, shell.tsx, ui.tsx, protected layout, shell tests. Four destinations; language context; focused study shell; keyboard access and shared spacing/type/color.
- [ ] Today and progress: dashboard/page.tsx, progress/page.tsx, dashboard skeleton and associated tests; real metrics and actionable next session. Add full-history analytics only with a verified server contract and tests.
- [ ] Study: study.tsx, lesson-modes.tsx, teaching-activity.tsx, speech-coach.tsx, learn/[mode], cronograma/dia and tests. Focus, clear controls, feedback and completion; preserve drafts/error behavior.
- [ ] Supporting screens: cronograma, learn hub, onboarding, languages, placement, profile, settings, auth, mode-card and tests. Editorial grouping, responsive hierarchy, real states.
- [ ] Integration: run frontend test suite, lint, typecheck, build; backend tests if API changes; inspect rendered screens and correct regressions; document results.

## Verification
Behavioral tests must exercise navigation/focus/real data or response preservation rather than CSS implementation details. Existing tests guard learning and authentication flows. New graph tests distinguish missing data from zero. Run tests scoped to each change, then full frontend checks. Inspect mobile and desktop with locally mocked API fixtures clearly separated from production.

## Progress ledger
Initial checkout clean. User explicitly authorized all blueprint changes and forbids commits/deploy. Shared foundation owner is root; screen tasks have disjoint file ownership. Shared dependencies: existing UI primitives and semantic CSS tokens, no new required props.
