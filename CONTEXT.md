# Project Context

> Live status of the project: where we are, what comes next, and how to work here.
> Updated at the close of each week/milestone. Last updated: **2026-06-05**.

---

## What this is

A **persistent urban simulation**: a city that evolves autonomously over time, even
while the user is offline. The goal is not a video game but an **artificial society**
that generates emergent phenomena (mobility, economy, relationships, health, death).
The city is the protagonist.

> The city does not exist for the player. The player exists inside the city.

Source documents:
- **`simulacion_urbana_v2.md`** — vision and conceptual model (the *what* and *why*).
- **`plan_4_semanas.md`** — MVP execution plan with weekly gates.
- **`ARCHITECTURE.md`** — how it is built technically.
- **`DECISIONS.md`** — architecture decisions (ADRs) with their rationale.
- **`CHANGELOG.md`** — what changed and when.

---

## Current status

| Aspect              | Status                                                              |
|---------------------|---------------------------------------------------------------------|
| Phase               | **Week 4 — Society** (relationships, contagion, death)             |
| Week 1 (Core)       | 🟡 In progress: engine beats, ticks and records events             |
| Week 2 (Identity)   | ✅ Traits, needs, wellbeing, decision, economy (v0.2.0-alpha)      |
| Week 3 (Trajectory) | ✅ Episodic memory, transient emotion, dynamic goals (v0.3.0-alpha)|
| Week 4 (Society)    | 🟡 In progress                                                     |
| Platform            | ✅ Facade + Pygame client + executables (release v0.1.0)           |
| Active layers       | Layer 1 (Persons · Households · Work · Mobility · minimal economy) |
| Tests               | ✅ 55 green tests (invariants, reproducibility, facade, UI, gates Wk 2 & 3) |

Legend: ✅ done · 🟡 in progress · ⏳ next · ⬜ pending

### What EXISTS and WORKS today

**Engine (headless)**
- Deterministic core: `python -m citysim --days 30` seeds 100 persons · 30 households ·
  50 places, ticks one month and records ~3.7k events.
- Seeded and injected RNG (`rng.py`), multi-scale scheduler (hourly/daily/monthly/population),
  eventlog that applies and persists, invariants checked after every run.
- **Week 2 — Identity**: traits (5 dimensions, population-level variation), psychological
  needs (5), wellbeing weighted by traits, satisficing decision, minimal economy
  (work → income, consume → expense, money conservation invariant).
- **Week 3 — Trajectory**: episodic memory with decay, transient emotion via appraisal
  (never stored — ADR-0006), dynamic goals (`earn_more`, `find_work`); past history
  modulates current decision scores.
- `Relationship` entity in `state/` and `EventType` entries for Week 4 (structural
  scaffold in place).

**Desktop client** (`make ui`)
- World creation (seed, persons, households, businesses), neighborhood canvas, event feed,
  clock controls (play/pause, speed, step by tick), save/load.
- **Agent mobility**: dots move between home and workplace each tick, reflecting the
  chosen action (`location_id` updated on `ACTION_CHOSEN`).
- **Camera**: scroll wheel / trackpad = zoom (0.2×–8.0×, centered on cursor);
  right or middle mouse drag = pan; H = reset.
- **Color by action**: work = yellow, socialize = violet, rest = blue, consume = green;
  dead agents = dark grey; legend in lower-left corner.
- **Place labels**: type + id ("Casa 3", "Emp. 7") below each place square; hidden below
  0.6× zoom to avoid clutter.
- **Person inspection panel**: click any agent to open a panel with state (wellbeing,
  health, energy), traits, needs, bipolar mood meter (Semana 3), active goals + progress.
- Facade layer isolates the engine from the client (read-only DTOs, ADR-0011).
- Full Dockerization: multi-stage image, compose, Makefile, CI matrix on 3.11 + 3.12.
- Executables for Win/Mac/Linux via PyInstaller (release `v0.1.0`).
- **55 green tests**: invariants, reproducibility, facade, UI, gates Wk 2 & 3.

### What is still a STUB (deliberate NotImplementedError)
- Week 4 systems: `relations`, `contagion`, `death`.
- Offline projection (`projector`) and observers (Week 4).

> Note on determinism: with only `aging` (seed-independent), the event log does not yet
> diverge between seeds; the seed today only affects the initial population. Log
> divergence by seed will come with the stochastic systems. The test documents this
> and will need to be strengthened at that point.

---

## Immediate next step

**Week 4 — Society** is active. Remaining items:
1. `systems/relations.py`: seed initial relationships + form new ones over time.
2. `systems/contagion.py`: moods spread through the network (proportional to bond strength).
3. `systems/death.py`: emergent death + consequence queue (grief, inheritance, household
   restructuring, memory trace in survivors).
4. Offline projection (`projector`) and one observer view (`observers/citizen.py`).

**Week 4 gate:** a well-connected death generates ripples in the network and economy;
a neighborhood shock produces a collective mood drop.

---

## MVP scale

```text
100 persons · 30 households · 20 businesses · 1 neighborhood · 1 simulated year
```

---

## Working conventions

- **Determinism first.** All randomness goes through the injected RNG. Never the
  global `random`. (ADR-0002)
- **Events for every change.** Systems do not mutate state; they emit `Event`. Only
  the `eventlog` applies. (ADR-0001)
- **`state/` is data only.** Logic goes in `systems/`. (ADR-0003)
- **Do not advance with a broken foundation.** If an invariant test fails, stop and
  fix it. No debt accumulates.
- **Do not activate layers all at once.** Validate one at a time to distinguish
  emergence from bugs. (ADR-0005)
- **Agent richness is the priority.** Keep the economy minimal in the MVP;
  don't let it consume the focus.

## Language
- Documentation and comments: **English**.
- Code identifiers: **English** (`Person`, `Household`, `decide_action`).

---

## Active risks

- **Offline projection** — the biggest technical risk; addressed in Week 4.
- **Premature over-engineering** — at 100 agents, optimizing wastes time.
- **Absorbing economy** — tends to grow and steal focus; keep it minimal.
- **Skipping a gate** — without validating each milestone, emergence cannot be
  distinguished from bugs.
