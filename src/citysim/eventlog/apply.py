"""Aplicadores de eventos: cómo cada EventType muta el World.

Único lugar del sistema con escritura sobre el estado (ADR-0001). Se registra un
aplicador por EventType. Los EventType sin aplicador todavía son no-ops conscientes
(se irán implementando por semana/capa).
"""

from __future__ import annotations

from typing import Callable

from ..state.enums import EventType
from ..state.event import Event
from ..state.person import Goal, MemoryTrace
from ..state.world import World

Applier = Callable[[World, Event], None]

_APPLIERS: dict[EventType, Applier] = {}


def applier(event_type: EventType) -> Callable[[Applier], Applier]:
    """Decorador para registrar el aplicador de un EventType."""

    def register(fn: Applier) -> Applier:
        _APPLIERS[event_type] = fn
        return fn

    return register


def apply_event(world: World, event: Event) -> None:
    """Aplica un evento al mundo usando el aplicador registrado.

    Si no hay aplicador para el tipo, es un no-op (se implementará más adelante).
    """
    fn = _APPLIERS.get(event.type)
    if fn is not None:
        fn(world, event)


# --- Aplicadores Semana 1 (mínimos) -----------------------------------------

@applier(EventType.TICK)
def _apply_tick(world: World, event: Event) -> None:
    world.tick = event.tick


@applier(EventType.AGED)
def _apply_aged(world: World, event: Event) -> None:
    pid = event.payload["person_id"]
    delta = event.payload.get("delta_years", 0.0)
    person = world.persons.get(pid)
    if person is not None and person.alive:
        person.age += delta


@applier(EventType.DEATH)
def _apply_death(world: World, event: Event) -> None:
    pid = event.payload["person_id"]
    person = world.persons.get(pid)
    if person is not None and person.alive:
        person.alive = False
        world.dead_count += 1


@applier(EventType.BIRTH)
def _apply_birth(world: World, event: Event) -> None:
    # El seeder/sistema de natalidad construye la Person y la pasa en el payload.
    person = event.payload["person"]
    world.persons[person.id] = person
    world.born_count += 1


# --- Aplicadores Semana 2 (identidad y economía mínima) ----------------------

def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


# Efectos por tick de cada acción: (delta energía, necesidad reforzada, delta necesidad).
# Las claves de acción son las de systems/decision.py (work/socialize/rest/consume).
_ACTION_EFFECTS: dict[str, tuple[float, str | None, float]] = {
    "work": (-0.05, "purpose", 0.05),
    "socialize": (-0.03, "belonging", 0.12),
    "rest": (0.10, None, 0.0),
    "consume": (-0.01, "stimulation", 0.12),
}


@applier(EventType.NEEDS_RECALCULATED)
def _apply_needs(world: World, event: Event) -> None:
    person = world.persons.get(event.payload["person_id"])
    if person is None or not person.alive:
        return
    n = person.needs
    n.belonging = event.payload["belonging"]
    n.autonomy = event.payload["autonomy"]
    n.purpose = event.payload["purpose"]
    n.security = event.payload["security"]
    n.stimulation = event.payload["stimulation"]


@applier(EventType.WELLBEING_RECALCULATED)
def _apply_wellbeing(world: World, event: Event) -> None:
    person = world.persons.get(event.payload["person_id"])
    if person is not None and person.alive:
        person.wellbeing = event.payload["wellbeing"]


@applier(EventType.ACTION_CHOSEN)
def _apply_action(world: World, event: Event) -> None:
    person = world.persons.get(event.payload["person_id"])
    if person is None or not person.alive:
        return
    action = event.payload["action"]
    person.current_action = action

    # Mover a la persona a su lugar según la acción.
    if action == "work" and person.employer_id is not None:
        person.location_id = person.employer_id
    elif person.household_id is not None:
        hh = world.households.get(person.household_id)
        if hh is not None:
            person.location_id = hh.dwelling_id

    d_energy, need, d_need = _ACTION_EFFECTS.get(action, (0.0, None, 0.0))
    person.energy = _clamp01(person.energy + d_energy)
    if need is not None:
        setattr(person.needs, need, _clamp01(getattr(person.needs, need) + d_need))


@applier(EventType.INCOME)
def _apply_income(world: World, event: Event) -> None:
    person = world.persons.get(event.payload["person_id"])
    if person is not None and person.alive:
        person.money += event.payload["amount"]


@applier(EventType.EXPENSE)
def _apply_expense(world: World, event: Event) -> None:
    person = world.persons.get(event.payload["person_id"])
    if person is not None and person.alive:
        person.money -= event.payload["amount"]

# --- Aplicadores Semana 3 (trayectoria) --------------------------------------

@applier(EventType.MEMORY_UPDATED)
def _apply_memory(world: World, event: Event) -> None:
    person = world.persons.get(event.payload["person_id"])
    if person is None or not person.alive:
        return
    person.memory = [
        MemoryTrace(
            event_type=t["event_type"],
            valence=t["valence"],
            intensity=t["intensity"],
            age_ticks=t["age_ticks"],
        )
        for t in event.payload["traces"]
    ]


@applier(EventType.GOAL_FORMED)
def _apply_goal_formed(world: World, event: Event) -> None:
    person = world.persons.get(event.payload["person_id"])
    if person is None or not person.alive:
        return
    person.goals.append(Goal(
        kind=event.payload["kind"],
        target=event.payload["target"],
    ))


@applier(EventType.GOAL_ACHIEVED)
def _apply_goal_achieved(world: World, event: Event) -> None:
    person = world.persons.get(event.payload["person_id"])
    if person is None or not person.alive:
        return
    kind = event.payload["kind"]
    for goal in person.goals:
        if goal.kind == kind and goal.active:
            goal.active = False
            break
    # Deja huella positiva en la memoria del agente
    person.memory.append(MemoryTrace(
        event_type=f"goal_achieved_{kind}",
        valence=0.8,
        intensity=0.7,
        age_ticks=0,
    ))


@applier(EventType.GOAL_ABANDONED)
def _apply_goal_abandoned(world: World, event: Event) -> None:
    person = world.persons.get(event.payload["person_id"])
    if person is None or not person.alive:
        return
    kind = event.payload["kind"]
    for goal in person.goals:
        if goal.kind == kind and goal.active:
            goal.active = False
            break
    # Deja huella negativa en la memoria del agente
    person.memory.append(MemoryTrace(
        event_type=f"goal_abandoned_{kind}",
        valence=-0.5,
        intensity=0.6,
        age_ticks=0,
    ))
