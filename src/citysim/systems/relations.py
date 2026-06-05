"""relations — vínculos con peso (Capa 1, Semana 4, escala diaria).

Forma nuevos vínculos cuando dos personas comparten ubicación: si dos personas
coinciden en el mismo lugar, pueden volverse conocidas. La formación es probabilística
y usa el RNG sembrado para preservar el determinismo.

No muta directamente: emite RELATIONSHIP_FORMED.
"""

from __future__ import annotations

from collections import defaultdict

from ..state.enums import EventType, Layer, RelType, TimeScale
from ..state.event import Event
from ..state.world import World
from .base import SystemSpec, TickContext

_FORM_PROB = 0.025       # probabilidad de formar relación al compartir lugar
_MAX_SAMPLES = 4         # pares a evaluar por cada cluster de ubicación


def step(world: World, ctx: TickContext) -> list[Event]:
    events: list[Event] = []

    by_loc: dict[int, list] = defaultdict(list)
    for p in world.living_persons():
        if p.location_id is not None:
            by_loc[p.location_id].append(p)

    existing: set[tuple[int, int]] = {
        (min(r.a_id, r.b_id), max(r.a_id, r.b_id))
        for r in world.relationships.values()
    }

    next_id = world.next_relationship_id

    for loc_id, persons in by_loc.items():
        if len(persons) < 2:
            continue
        place = world.places.get(loc_id)
        rel_type = (
            RelType.WORK.value
            if place and place.type.value == "business"
            else RelType.FRIEND.value
        )
        n_samples = min(_MAX_SAMPLES, len(persons) * (len(persons) - 1) // 2)
        for _ in range(n_samples):
            i = ctx.rng.randint(0, len(persons) - 1)
            j = ctx.rng.randint(0, len(persons) - 2)
            if j >= i:
                j += 1
            a, b = persons[i], persons[j]
            pair = (min(a.id, b.id), max(a.id, b.id))
            if pair in existing or ctx.rng.random() >= _FORM_PROB:
                continue
            events.append(Event(
                type=EventType.RELATIONSHIP_FORMED,
                tick=ctx.tick,
                scale=TimeScale.DAILY,
                payload={
                    "id": next_id,
                    "a_id": a.id,
                    "b_id": b.id,
                    "type": rel_type,
                    "strength": ctx.rng.uniform(0.15, 0.35),
                    "reciprocity": 0.5,
                },
            ))
            existing.add(pair)
            next_id += 1

    return events


SPEC = SystemSpec(
    name="relations",
    fn=step,
    scale=TimeScale.DAILY,
    layer=Layer.L1_BASE,
    order=10,
)
