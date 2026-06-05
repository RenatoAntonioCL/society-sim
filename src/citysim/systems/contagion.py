"""contagion — difusión de ánimo por la red de relaciones (Capa 1, Semana 4, escala diaria).

Si los vecinos bien conectados tienen un ánimo cargado, parte de ese estado se
contagia. El contagio es proporcional a la fuerza del vínculo y actúa añadiendo
una traza de memoria ("social_influence") que decae con el tiempo igual que
cualquier otro recuerdo. Así, el sistema emocional ya existente lo integra sin
cambios y la tristeza colectiva se desvanece cuando el origen desaparece.

Solo emite si el efecto del cluster supera un umbral: los vínculos débiles no
generan ruido constante en el log.
"""

from __future__ import annotations

from collections import defaultdict

from ..state.enums import EventType, Layer, TimeScale
from ..state.event import Event
from ..state.world import World
from ..systems import emotion as emotion_sys
from .base import SystemSpec, TickContext

_INFLUENCE_THRESHOLD = 0.15     # ánimo mínimo del cluster para que haya contagio
_CONTAGION_SCALE = 0.45         # atenuación del ánimo vecinal al transferir
_MAX_INTENSITY = 0.55           # techo de la traza de influencia social


def step(world: World, ctx: TickContext) -> list[Event]:
    events: list[Event] = []

    # Índice: person_id → [(emoción_del_vecino, strength)]
    neighbors: dict[int, list[tuple[float, float]]] = defaultdict(list)
    for rel in world.relationships.values():
        a = world.persons.get(rel.a_id)
        b = world.persons.get(rel.b_id)
        if a is None or b is None or not a.alive or not b.alive:
            continue
        emotion_a = emotion_sys.compute(a)
        emotion_b = emotion_sys.compute(b)
        neighbors[rel.b_id].append((emotion_a, rel.strength))
        neighbors[rel.a_id].append((emotion_b, rel.strength))

    for person in world.living_persons():
        nbrs = neighbors.get(person.id)
        if not nbrs:
            continue
        total_strength = sum(s for _, s in nbrs)
        if total_strength < 0.01:
            continue
        weighted_avg = sum(e * s for e, s in nbrs) / total_strength
        if abs(weighted_avg) < _INFLUENCE_THRESHOLD:
            continue

        valence = max(-1.0, min(1.0, weighted_avg * _CONTAGION_SCALE))
        intensity = min(_MAX_INTENSITY, total_strength / max(1, len(nbrs)))

        existing = [
            {
                "event_type": t.event_type,
                "valence": t.valence,
                "intensity": t.intensity,
                "age_ticks": t.age_ticks,
            }
            for t in person.memory
        ]
        events.append(Event(
            type=EventType.MEMORY_UPDATED,
            tick=ctx.tick,
            scale=TimeScale.DAILY,
            payload={
                "person_id": person.id,
                "traces": existing + [
                    {
                        "event_type": "social_influence",
                        "valence": valence,
                        "intensity": intensity,
                        "age_ticks": 0,
                    }
                ],
            },
        ))

    return events


SPEC = SystemSpec(
    name="contagion",
    fn=step,
    scale=TimeScale.DAILY,
    layer=Layer.L1_BASE,
    order=28,
)
