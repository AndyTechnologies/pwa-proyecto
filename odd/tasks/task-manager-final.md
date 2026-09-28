# Feature: Task Manager — Proyecto Final PW Avanzada

**Feature doc:** `odd/tasks/task-manager-final.md`
**Engram mirror:** `odd/task-manager-final/tasks`
**Branch:** `feat/task-manager`
**Normative source:** `/home/andy/Downloads/ProyectoFinalPWAvanzadav4.pdf` (1 page, 8 functional requirements, 4 cortes, no DRF, all CBVs)

## Goal

Build the academic final project: a Django task manager with ownership, three-level
visibility, tags, filtering/sorting, auth, CBVs only, Bootstrap 5, plus full automated
tests, technical documentation, ADRs, a Spanish academic paper, a traceability matrix
and a compliance report against the assignment.

## Non-goals

- No DRF, no API layer, no function-based views.
- No invented academic requirements (e.g. "due_date cannot be in the past").
- No microservices, CQRS, or Event Sourcing.
- No extra dependencies beyond Django + Bootstrap 5.

## Architecture decisions (to be recorded as ADRs)

- Monolithic modular Django MVT/MTV.
- All views Class-Based Views.
- Authorization enforced at queryset level, not in templates.
- Read policy and write policy are distinct code paths.
- Sort/filter params validated against a server-side whitelist.

## Tasks

| # | Task | Corte | Commit | Status |
|---|------|-------|--------|--------|
| 1 | FASE 0 — Auditoría inicial → `docs/initial-audit.md` | — | — | in_progress |
| 2 | Reestructurar `core` → `tasks`, static/templates a raíz | — | — | pending |
| 3 | FASE 1 — Prototipo estático Bootstrap 5 | Sem 3 | — | pending |
| 4 | FASE 2 — Modelos, migraciones, Admin | Sem 5 | — | pending |
| 5 | FASE 3a — Auth (registro/login/logout CBVs) | Sem 7 | — | pending |
| 6 | FASE 3b — CRUD CBVs con ownership | Sem 7 | — | pending |
| 7 | FASE 3c — Visibilidad, orden, filtros, tags | Sem 7 | — | pending |
| 8 | FASE 4a — Tests automatizados | Sem 9 | — | pending |
| 9 | FASE 4b — Documentación técnica + ADRs | Sem 9 | — | pending |
| 10 | FASE 4c — Trazabilidad + reporte de cumplimiento | Sem 9 | — | pending |
| 11 | FASE 4d — Paper académico en español | Sem 9 | — | pending |
| 12 | Verificación final y auditoría contra consigna | Sem 9 | — | pending |

## Resolved ambiguities (assignment §62 — resolve and document, do not ask)

| Ambiguity | Resolution | Where documented |
|---|---|---|
| ¿Qué niveles tiene `priority`? | `LOW` / `MEDIUM` / `HIGH` via `IntegerChoices` with explicit ordering | ADR + data-model.md |
| ¿Puede una tarea pública aparecer en el listado general? | No. Only the public detail route is anonymous-reachable | ADR-005 |
| ¿El owner puede cambiar una tarea compartida a privada? | Yes — visibility is a mutable owner field | ADR-005 |
| ¿Se permite reabrir una tarea completada? | Yes, via edit form and the toggle action | RF-06 + tests |
| ¿Qué ocurre tras el registro? | Redirect to login (not auto-login) — avoids surprising session state | RF-01 + tests |
| ¿Las etiquetas son únicas? | `Tag.name` unique, case-insensitive reuse via slug | RF-10 + tests |
| ¿`due_date` puede estar en el pasado? | Yes — not forbidden, not invented | RF-03 + tests |
| ¿Borrado físico o lógico? | Physical delete (simplest, no soft-delete requirement) | ADR + data-model.md |

## Verification gates

Every task closes only when: code + validation + authorization + tests + docs.
No requirement is reported as met without code or test evidence.
