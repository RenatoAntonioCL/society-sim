# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adopts [Semantic Versioning](https://semver.org/). While the MVP is under
development, the version stays in `0.x` and the API is considered unstable.

## [Unreleased]

### Added
- **Week 4 — Society**: social network, contagion and emergent death.
  - **`state/relationship.py`** — `Relationship` entity with `strength` and `reciprocity`
    as first-class fields. `World` gains `next_relationship_id` and a
    `relationships` index.
  - **`seed/seeder.py`**: initial bonds seeded deterministically — family pairs
    (strength 0.65–0.95), work colleague pairs (0.30–0.55) and up to 80 random
    friendships (0.20–0.55).
  - **`systems/relations.py`** (daily, order 10): new bonds form when two persons share
    a location; formation probability 2.5%; emits `RELATIONSHIP_FORMED`.
  - **`systems/contagion.py`** (daily, order 28): weighted-average neighbor emotion
    is injected as a `"social_influence"` `MemoryTrace` when the cluster signal
    exceeds 0.15; decays naturally through the existing emotion pipeline.
  - **`systems/death.py`** (population scale, order 20): daily mortality probability
    driven by age (exponential above 60) and health (up to 3× multiplier, capped at
    25%/day). Two-pass: collects all dying persons first, then emits `DEATH`,
    `INHERITANCE` (money split among living household members) and `MEMORY_UPDATED`
    grief traces for bonds with strength ≥ 0.40.
  - **`eventlog/apply.py`**: three new appliers — `RELATIONSHIP_FORMED`,
    `RELATIONSHIP_CHANGED`, `INHERITANCE`.
  - **`scheduler/clock.py`**: registers the three new systems; fixes the static-RNG
    bug (derive key now includes the tick, so stochastic systems produce different
    draws each day while remaining deterministic for a given seed).
  - **`tests/test_week4_society.py`**: 12 gate tests — mortality curve, grief
    threshold (≥ 0.40 gets grief, < 0.40 does not), seed coverage, integration gate
    (death → grief → contagion ripple). **67 green tests total.**

### Fixed
- **Agent mobility in the desktop view**: agents were always rendered at their home
  position regardless of their current action. `eventlog/apply.py` — `_apply_action`
  now updates `Person.location_id` when applying `ACTION_CHOSEN`: workers move to their
  `employer_id`; all others return to their household dwelling. Dots now migrate between
  places each tick.
- **Static RNG per tick** (`scheduler/clock.py`): `rng.derive(spec.name)` produced
  the same sub-seed every tick because the XOR was static. Fixed by deriving
  `f"{spec.name}_{tick}"` so each tick gets a unique sub-stream.

### Added (desktop)
- **Desktop client — camera: pan and zoom**: scroll wheel (zoom 0.2×–8.0×), right/
  middle-click drag (pan), H key (reset). All draw calls go through `_w2s()` /
  `_s2w()`, so selection hit-testing stays correct at any zoom level.
- **Desktop client — agent color by action**: work = yellow, socialize = violet,
  rest = blue, consume = green; dead = dark grey. Legend in the lower-left corner.
- **Desktop client — place labels**: type + id below each place square (e.g. "Casa 3",
  "Emp. 7"), hidden below 0.6× zoom.
- **Desktop client — person inspection panel**: click an agent to inspect it. The
  right panel shows the person's state (wellbeing, health, energy), the five traits
  and the five needs as color-coded `[0,1]` bars, plus age, money and current action;
  the selected dot gets an accent ring. Click empty space or press `Esc` to close.
  - `layout.person_at()`: pure (pygame-free) hit-test that resolves a click to the
    nearest agent within a radius — keeps selection testable headless.
  - `SimController.select()` / `selected_person()`: selection state in the presenter;
    the DTO is re-read from the facade each frame, so the panel tracks the live agent.
  - 5 new client tests (selection lifecycle + hit-test).
- **Facade — trajectory exposed in `PersonDTO`**: the Week 3 trajectory (emotion,
  memory, goals) is now readable by clients. `PersonDTO` gains `emotion` (recomputed
  from memory via `systems.emotion`, never stored — ADR-0006), `memory`
  (`MemoryTraceDTO`) and `goals` (`GoalDTO`). The inspection panel uses them: a bipolar
  **Ánimo** meter (`[-1,1]`) and an **Objetivos** section with active goals + progress.
  - 1 new facade test (emotion matches the pure function; memory/goals form over a run).

## [0.3.0-alpha] — 2026-06-02

**Trajectory** milestone (Week 3): past lived experience changes present behavior.
Gate passed: two agents identical in traits but with different histories decide
differently today; emotion decays at a rate consistent with resilience.
The packaged version is `0.3.0a1` (PEP 440); the milestone tag is `v0.3.0-alpha`.

### Added
- **Week 3 — Trajectory**: the past weighs in.
  - **`systems/memory.py`** (daily scale): ages episodic traces (`age_ticks += 1`)
    and records significant states (low wellbeing, unemployment with dropped purpose).
    Emits `MEMORY_UPDATED`; the applier rebuilds `Person.memory` from the payload.
  - **`systems/emotion.py`**: pure function `compute(person) → float [-1, 1]`. Transient
    emotional signal computed as a weighted sum of valences with exponential decay
    (unnormalized) — a very old memory loses absolute weight and mood converges to 0.
    High resilience → faster decay rate → faster recovery. Never stored; recomputed
    every tick in `decision.py`.
  - **`systems/goals.py`** (daily scale): dynamic goals `earn_more` and `find_work`.
    Formed when need and trait indicate it; achieved when the condition is met.
    Achievement leaves a positive memory trace; abandonment leaves a negative one.
  - **`systems/decision.py`**: `_scores()` incorporates the emotional signal as an
    additive modifier (±0.10 × mood) on `work`, `rest` and `consume`. An agent with
    a recent unemployment memory lowers its `work` score and raises its `rest` score,
    potentially crossing the satisficing threshold toward inaction.
  - `EventType.MEMORY_UPDATED` added to the closed enum of types.
  - Appliers in `eventlog/apply.py` for `MEMORY_UPDATED`, `GOAL_FORMED`,
    `GOAL_ACHIEVED` and `GOAL_ABANDONED`.
- **`package.yml` workflow fix**: `prerelease: ${{ contains(github.ref, '-') }}`
  to automatically mark tags with a dash (alpha/beta/rc) without manual intervention.
- 8 new tests (`test_week3_trajectory.py`): emotional signal with no memory, with
  negative/positive memory, decay over time, resilience effect, and the central gate
  (same traits + different history → different action). **49 green tests total.**

## [0.2.0-alpha] — 2026-06-01

**Identity** milestone (Week 2): agents stop being flat — traits, needs, wellbeing
dependent on them, satisficing decision and minimal economy. Gate passed.
The packaged version is `0.2.0a1` (PEP 440); the milestone tag is `v0.2.0-alpha`.

### Added
- **Week 2 — Identity** (ADR-0014): agents stop being flat.
  - **Traits** in `Person`, seeded with population-level variation (sociability,
    ambition, risk tolerance, conscientiousness, resilience).
  - New systems (Layer 1, hourly scale): `needs` (recalculates needs), `wellbeing`
    (wellbeing weighted by traits, not just money), `decision` (satisficing,
    deterministic, ADR-0007) and `economy` (work yields income, consumption spends).
  - `Person.current_action` as activity state; the seeder employs persons of working age.
  - **Money conservation invariant** (ARCHITECTURE §10 #1) + [0,1] ranges for
    traits/needs. Strengthened determinism: different seeds ⇒ different logs.
  - Facade: `PersonDTO` exposes `traits`, `needs` and `current_action` (additive).
  - Gate verified by test: two agents with similar economy and opposite traits decide
    differently in a consistent way (ambitious → work, sociable → socialize).

## [0.1.0] — 2026-06-01

First milestone with a **downloadable desktop application**: core + facade + Pygame
client + packaging to executables (Win/Mac/Linux).

### Added
- **Executable packaging** (PyInstaller, ADR-0013): the client is packaged into native
  executables (onefile) for Windows, macOS and Linux. `packaging/` contains the
  versioned `.spec` and entry script; a new `package.yml` workflow builds one binary
  per OS in a matrix, validates it with a headless `--smoke` mode and uploads it as
  an artifact (and attaches it to a Release on `v*` tags). Pygame uses its built-in
  font (no OS font dependency) and worlds are saved in a user data directory
  (`citysim_desktop/paths.py`). PyInstaller is an optional extra `[build]`; the core
  remains dependency-free.
- **Desktop client** (`citysim_desktop/`, ADR-0012): first visual interface in Pygame,
  connected only to the facade. World creation screen (seed, persons, households,
  businesses), neighborhood view (places + persons with deterministic layout by id),
  event feed, clock controls (play/pause, speed, step) and save/load. Split into
  **presenter** (`controller.py`/`layout.py`, pure Python, testable without a display)
  and **view** (`view.py`, Pygame). Pygame is an **optional** dependency
  (`pip install ".[ui]"`); the core remains dependency-free. Run with
  `python -m citysim_desktop`. 10 new presenter/layout tests (no display).
- **Facade layer** (`citysim/facade/`, ADR-0011): `Simulation` class as the single
  public surface for future clients (desktop UI, graphics engine). Exposes create,
  advance (`advance`/`advance_days`), read state and recent events,
  `check_invariants`, and `save`/`load`. Delivers **read-only DTOs** (`PersonDTO`,
  `HouseholdDTO`, `PlaceDTO`, `RelationshipDTO`, `EventDTO`, `WorldStateDTO`); never
  the internal `World` entities. The core was not touched. Saved by *replay*
  (`config + ticks`), exact thanks to determinism (ADR-0002) and without serializing
  pointers (ADR-0004).
- **Continuous integration (GitHub Actions)**: `ci.yml` workflow that on every push/PR
  to `main` runs the suite on Python 3.11 and 3.12 and, in parallel, builds the Docker
  image (stages `test` and `runtime`) with a smoke run. Status badge in README.
- **Project Dockerization** (portfolio-oriented):
  - Multi-stage `Dockerfile` (`builder` / `test` / `runtime`): installs in an isolated
    venv, runs the suite in the `test` stage and produces a minimal final image
    (~220 MB) with non-root user `sim` and OCI labels.
  - `docker-compose.yml` with `sim` (execution, `./runs` volume) and `tests` services.
  - `Makefile` with shortcuts: `build`, `run`, `test`, `shell`, `clean`, `help`.
  - `.dockerignore`.
  - README: "Getting started with Docker" section as the recommended path.

### Verified
- `docker build --target test` → 7 green tests inside the container.
- `docker run --rm citysim --days 30` reproduces the same log fingerprint as the local
  run (`4c2ff62fcf8a4d38…`): determinism holds across environments.
- `docker compose config` valid; `compose run sim/tests` work.

### To do (complete Week 1 / open Week 2)
- Strengthen the determinism gate when stochastic systems are introduced.
- Week 2: traits + needs in `Person`/seeder, `wellbeing`, satisficing decision.

---

## [0.0.1] — 2026-06-01

### Added
- Project architecture documentation:
  - `ARCHITECTURE.md` — high-level view, package structure, event flow,
    determinism, multi-scale clock, activatable layers and plan→architecture map.
  - `DECISIONS.md` — 10 initial ADRs (events as source of truth, determinism,
    pure state, references by id, layers as flags, three psychological scales,
    satisficing decision, multi-scale clock, stack, emergent death).
  - `CONTEXT.md` — live project status, next steps and conventions.
  - `CHANGELOG.md` — this file. `README.md`.
- `src/citysim/` package following the base architecture from the plan: `state/`,
  `systems/`, `scheduler/`, `eventlog/`, `seed/`, `projector/`, `observers/`, with
  contracts (protocols, signatures) and closed-type `enums`.
- **Functional deterministic core (Week 1 skeleton):**
  - `rng.py` — seeded and injected RNG, with sub-stream derivation.
  - `state/` — pure models: `World`, `Person` (base state + placeholders for
    traits/needs/memory/goals), `Household`, `Place`, `Relationship`, `Event`.
  - `eventlog/` — emits, applies (one applier per `EventType`) and persists events;
    the only component with write access to state.
  - `scheduler/clock.py` — multi-scale clock (hourly/daily/monthly/population) with
    layer-filtered and ordered system registry.
  - `seed/seeder.py` — deterministic initial population (100·30·20·1).
  - `systems/aging.py` — first example system (aging).
  - `invariants.py` — population balance, valid ranges, referential integrity.
  - `__main__.py` — `python -m citysim` runs a simulation and reports invariants.
- `tests/` with `pytest`: 7 green tests (invariants after a run + reproducibility).
- Stubs with deliberate `NotImplementedError` for Week 2–4 systems, the `projector`
  and the Citizen observer.

### Verified
- `python -m citysim --days 30` runs cleanly: 100 persons, 50 places, ~3720 events.
- All 7 tests pass. Invariants green at initial state and after simulating.

### Notes
- Starting point: the vision (`simulacion_urbana_v2.md`) and plan (`plan_4_semanas.md`)
  documents already existed. This version adds the technical architecture and an engine
  skeleton that already ticks deterministically; agent **behavior** (decision, emotion,
  memory, society) is still stubbed.
