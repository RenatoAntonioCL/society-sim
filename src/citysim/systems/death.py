"""death — muerte emergente con cola de consecuencias (ADR-0010, Semana 4).

La muerte emerge de riesgo acumulado: edad y salud determinan la probabilidad diaria.
Después de morir, las consecuencias son:
  - Herencia: el dinero del fallecido se reparte entre los convivientes vivos.
  - Duelo: una huella negativa de alta intensidad aparece en la memoria de los
    allegados con vínculos fuertes, proporcional a la fuerza del vínculo.

El dolor se propaga: el duelo cambia el ánimo de los allegados, que el sistema
de contagión difunde al resto de la red. Una muerte bien conectada genera así
ondas observables en la sociedad (gate Semana 4).

Emite: DEATH · INHERITANCE · MEMORY_UPDATED (duelo).
"""

from __future__ import annotations

import math
from collections import defaultdict

from ..state.enums import EventType, Layer, TimeScale
from ..state.event import Event
from ..state.world import World
from .base import SystemSpec, TickContext

_BASE_MORTALITY = 0.00005        # probabilidad diaria para edad ≤ 60
_AGE_MORTALITY_START = 60        # umbral a partir del cual crece exponencialmente
_AGING_RATE = 0.08               # tasa del exponente por año sobre el umbral
_HEALTH_MOD = 2.0                # multiplicador máximo por salud deteriorada
_GRIEF_STRENGTH_MIN = 0.40       # fuerza mínima del vínculo para recibir duelo


def _mortality_prob(age: float, health: float) -> float:
    """Probabilidad diaria de morir en función de edad y salud. Limitada al 25%."""
    if age <= _AGE_MORTALITY_START:
        base = _BASE_MORTALITY
    else:
        base = _BASE_MORTALITY * math.exp(_AGING_RATE * (age - _AGE_MORTALITY_START))
    health_modifier = 1.0 + _HEALTH_MOD * (1.0 - health)
    return min(0.25, base * health_modifier)


def step(world: World, ctx: TickContext) -> list[Event]:
    events: list[Event] = []

    # Índice de relaciones: person_id → [(other_id, strength)]
    rel_index: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for rel in world.relationships.values():
        rel_index[rel.a_id].append((rel.b_id, rel.strength))
        rel_index[rel.b_id].append((rel.a_id, rel.strength))

    # Primera pasada: decidir quién muere en este tick
    dying: set[int] = set()
    for person in world.living_persons():
        prob = _mortality_prob(person.age, person.health)
        if ctx.rng.random() < prob:
            dying.add(person.id)

    # Segunda pasada: emitir consecuencias para cada fallecido
    for pid in dying:
        person = world.persons[pid]

        events.append(Event(
            type=EventType.DEATH,
            tick=ctx.tick,
            scale=TimeScale.POPULATION,
            payload={"person_id": pid, "age": person.age},
        ))

        # Herencia: repartir dinero entre convivientes vivos (excluir otros moribundos)
        if person.household_id is not None:
            hh = world.households.get(person.household_id)
            if hh is not None:
                heirs = [
                    mid for mid in hh.member_ids
                    if mid != pid
                    and mid not in dying
                    and world.persons.get(mid) is not None
                    and world.persons[mid].alive
                ]
                if heirs and person.money > 0:
                    share = person.money / len(heirs)
                    for heir_id in heirs:
                        events.append(Event(
                            type=EventType.INHERITANCE,
                            tick=ctx.tick,
                            scale=TimeScale.POPULATION,
                            payload={"from_id": pid, "heir_id": heir_id, "amount": share},
                        ))

        # Duelo: huella negativa en la memoria de los allegados con vínculo fuerte
        for other_id, strength in rel_index.get(pid, []):
            if strength < _GRIEF_STRENGTH_MIN or other_id in dying:
                continue
            other = world.persons.get(other_id)
            if other is None or not other.alive:
                continue
            existing = [
                {
                    "event_type": t.event_type,
                    "valence": t.valence,
                    "intensity": t.intensity,
                    "age_ticks": t.age_ticks,
                }
                for t in other.memory
            ]
            events.append(Event(
                type=EventType.MEMORY_UPDATED,
                tick=ctx.tick,
                scale=TimeScale.POPULATION,
                payload={
                    "person_id": other_id,
                    "traces": existing + [
                        {
                            "event_type": f"grief_{pid}",
                            "valence": -0.9,
                            "intensity": strength,
                            "age_ticks": 0,
                        }
                    ],
                },
            ))

    return events


SPEC = SystemSpec(
    name="death",
    fn=step,
    scale=TimeScale.POPULATION,
    layer=Layer.L1_BASE,
    order=20,
)
