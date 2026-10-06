# FR B1 legacy reuse implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement task by task; one independent review at the end.

**Goal:** Block incompatible historical lesson reuse and prepare a transaction-scoped repair of the confirmed incident without losing learner records.
**Architecture:** Share finite, known English markers between generated-content validation and stored-content delivery. Require a compatible native snapshot for declared/dynamic language pairs; preserve bounded legacy static Portuguese support. Invalidate only the confirmed lesson after checking the reviewed pending block. Keep its pointer until normal generation atomically installs a validated replacement.
**Tech Stack:** Existing FastAPI, SQLAlchemy, PostgreSQL/SQLite, pytest; no new dependency/schema/provider.
**Spec:** User request of 2026-10-06; PostgreSQL result for f2ab192f-36ef-42d0-b7aa-1038c8d230d2, OpenRouter/nvidia/nemotron-3.5-lightning, FR B1, native pt-BR.

## Constraints
- No frontend, migration 0016, Session Builder, mastery, entitlement, speech or pricing changes.
- No commit, push, deploy or production write during implementation.
- No content rewrite or DELETE. Preserve curriculum, enrollments, progress, historical lessons and answers.
- Missing JSON key and explicit JSON null must both be covered, without assuming SQL ->> distinguishes them.

## Tasks
- [x] Turn both incident xfails into ordinary failing tests; add old OpenRouter reuse, stored-title, target-alias, native mismatch and safe legacy tests.
- [x] Update editorial_validation and language_policy; pass stored title and authoritative target in progression/lesson delivery. Refuse invalid content without mutating references or historical payloads.
- [x] Add a default dry-run repair script hardcoded to the confirmed lesson, requiring explicit --apply and --block-id, with transaction, row locks, checked preconditions, rollback rehearsal and idempotence. Only lesson.status changes in this script.
- [x] Prove dry-run preservation, wrong-ID/status/ownership refusal, atomic rollback, and compatible replacement through normal generation.
- [x] Run focal and full backend suites, independent review, document exact production commands and save the result in the existing Second Brain note under 2bbf6b59c0cb0b5b. Memory written and read-back verified. General suite is not approved because of the excluded lexical mastery path below.

## Review focus
- Completed or concurrently changed blocks: refuse repair; preserve the historical pointer.
- Unknown/missing language provenance: do not stamp the current user's native onto historical data.
- Stored title differing from content JSON title: validate both.
- Explicitly null native metadata: refuse selected-native reuse just as mismatched metadata.
- Generation failure: old history and pointer survive; retries generate normally without returning contaminated material.

## Execution decisions
- Keep lesson_ref until replacement succeeds, rather than clearing it in the repair: this prevents stale completion of an unlinked block and preserves rollback/reference history. Script changes one status only; generation swaps the pointer in its existing transaction.
- Block complete/abandon on language_invalid, including a locked refreshed read on abandon; otherwise a pre-repair page could overwrite quarantine and change progress.
- Lock all rows whose preconditions are checked in the production repair. Serialize replacement of a quarantined pointer and refresh it after waiting. SQLite stale-identity tests do not certify live PostgreSQL concurrency.
- Final review found no remaining blocker in the bounded implementation. Final focal suite: 122 passed, 4 warnings. General backend run: 1 failed, 1559 passed, 38 warnings; remaining two files: 10 passed. Vocabulary module rerun: 1 failed, 13 passed. Diagnostic trace shows equal lapse/correct-signal timestamps excluded by unchanged memory_engine's strict comparison. Mastery excluded by user: do not alter it or call the general suite approved. No production write.
