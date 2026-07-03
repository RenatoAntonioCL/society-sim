# Roadmap

> Where the project is headed and how to follow its progress. Day-to-day progress is
> visible in **commits**, in the [CHANGELOG](./CHANGELOG.md) and in the checkboxes
> below. Live status and current technical detail: [CONTEXT.md](./CONTEXT.md).

The build plan is in [`plan_4_semanas.md`](./plan_4_semanas.md): each milestone closes
with a **validation gate** (a yes/no question). A gate must pass before moving on.
Each milestone maps to a version.

## Versioning

While the MVP is under construction, the version lives in `0.x` and the API is
unstable. Each weekly core milestone corresponds to an alpha release; the closed MVP
(all 4 gates) marks the first stable reference version. Alongside that sequence, there
was a **platform** milestone —`v0.1.0`, the downloadable desktop app— which is not one
of the 4 behavior gates but rather the delivery vehicle; that is why the core
milestones continue from `v0.2.0-alpha`.

| Version        | Milestone                     | Gate / criterion                                              | Status |
|----------------|-------------------------------|---------------------------------------------------------------|--------|
| `v0.0.x`       | Deterministic core (Wk. 1)   | Does the world tick deterministically and reproducibly?       | 🟡 In progress |
| `v0.1.0`       | Downloadable platform         | Desktop app: facade + Pygame client + executables (Win/Mac/Linux) | ✅ Done |
| `v0.2.0-alpha` | Identity (Wk. 2)             | Do agents look distinct from each other?                      | ✅ Done |
| `v0.3.0-alpha` | Trajectory (Wk. 3)           | Does the past weigh in? Is there credible irrationality?      | ✅ Done |
| `v0.4.0-alpha` | Society (Wk. 4)              | Does the network react to a death / shock?                    | 🟡 Gate passed, release pending |
| `v1.0.0`       | Closed MVP                   | All 4 gates passed: one reproducible, non-flat year           | ⬜ Pending |

Legend: ✅ done · 🟡 in progress · ⬜ pending

---

## v0.0.x — Deterministic core 🟡

An engine that beats: ticks deterministically and records events. No behavior yet.

- [x] Architecture, decisions (ADRs), context and changelog.
- [x] `citysim` package scaffold with contracts (state, systems, scheduler, eventlog).
- [x] Seeded and injected RNG; eventlog that applies and persists; multi-scale scheduler.
- [x] Deterministic seeder (100 persons · 30 households · 20 businesses · 1 neighborhood).
- [x] Invariants + tests (population balance, ranges, integrity, reproducibility).
- [x] Dockerization (multi-stage image, compose, Makefile).
- [ ] Aging with complete base demographics (births/deaths by age).
- [ ] **Gate:** two runs with the same seed ⇒ same log; invariants green after one year.

## v0.1.0 — Downloadable platform ✅

Delivery milestone (parallel to the core gates): turn the engine into a real,
downloadable desktop application, without requiring the user to have Python.

- [x] Facade layer (`citysim/facade/`): single public surface with read-only DTOs;
      save/load by replay (ADR-0011).
- [x] Pygame desktop client (`citysim_desktop/`): world creation, neighborhood view,
      event feed, clock controls, save/load (ADR-0012).
- [x] Packaging to executables (Win/Mac/Linux) with PyInstaller + tag-based release
      workflow (ADR-0013).
- [x] Release `v0.1.0` published with all three validated binaries (`--smoke`).

## v0.2.0-alpha — Identity ✅

Agents look distinct from each other. Breaks flatness.

- [x] Traits in `Person` (sociability, ambition, risk tolerance, conscientiousness, resilience).
- [x] Psychological needs (belonging, autonomy, purpose, security, stimulation).
- [x] Wellbeing weighted by traits, not just money.
- [x] Basic satisficing decision.
- [x] Minimal economy (Layer 1): work yields income, consumption spends.
- [x] **Gate:** two agents with similar economy but opposite traits decide differently.

## v0.3.0-alpha — Trajectory ✅

Past lived experience changes the present, with credible irrationality.

- [x] Episodic memory with decay.
- [x] Transient emotion via appraisal, decaying by resilience (never stored).
- [x] Dynamic goals (form, pursue, achieve or abandon).
- [x] Memory → decision link (a layoff raises risk aversion).
- [x] **Gate:** two identical agents with different histories behave differently today.

## v0.4.0-alpha — Society ⬜

Actions ripple through the network and death carries weight.

- [x] `Relationship` with type, strength, reciprocity and history.
- [x] Social contagion through the network, proportional to bond strength.
- [x] Emergent death system + consequence queue (grief, inheritance, household, trace).
- [x] Offline projection (deterministic vs stochastic).
- [x] One observer view (Citizen or Analyst).
- [x] **Gate:** a well-connected death generates ripples in the network and economy;
      a neighborhood shock produces a collective mood drop.

## v1.0.0 — Closed MVP ⬜

All 4 gates passed: one simulated year, reproducible, with agents that look distinct,
remember, feel, influence each other and die leaving a trace.

---

## After the MVP (ideas, out of scope for now)

- Layer 2 (richer economy: savings, commerce, investment) and remaining layers as flags.
- More observers and a real UI.
- Deeper offline projection for long absences.
- Publishing the Docker image to a registry (CI already runs build + tests on push).
- **Signing and notarizing executables** (Apple Developer on macOS, code signing on
  Windows) so they open without Gatekeeper/SmartScreen warnings. Today the binaries are
  unsigned and require a manual step when first opened (see [ADR-0013](./DECISIONS.md)).

## How to follow progress

- **Commits**: the day-to-day work.
- **[CHANGELOG.md](./CHANGELOG.md)**: what changed in each version.
- **[CONTEXT.md](./CONTEXT.md)**: live status and the concrete next step.
- **Releases / tags**: each alpha milestone is tagged.
