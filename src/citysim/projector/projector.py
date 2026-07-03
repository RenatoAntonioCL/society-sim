"""Proyección offline (Semana 4).

Al reconectar NO se simula tick a tick el tiempo ausente: se proyecta un estado
consistente separando procesos por naturaleza:

  Deterministas (calculables en el salto): envejecimiento y avance del reloj.
  Estocásticos (muestreados una vez sobre el intervalo, no simulados): muerte, con
    probabilidad acumulada 1-(1-p_diaria)^días.

No muta el World a mano: emite eventos y los aplica por el eventlog (ADR-0001).
"""

from __future__ import annotations

from ..eventlog.apply import apply_event
from ..rng import Rng
from ..state.enums import EventType, TimeScale
from ..state.event import Event
from ..state.world import World
from ..systems.aging import _YEARS_PER_DAY
from ..systems.death import _mortality_prob


def project_forward(world: World, elapsed_days: int, rng: Rng) -> World:
    """Proyecta el mundo `elapsed_days` hacia adelante sin simular cada tick."""
    if elapsed_days < 0:
        raise ValueError("elapsed_days no puede ser negativo")
    if elapsed_days == 0:
        return world

    # Determinista: envejecer a cada persona viva de una sola vez (no día a día).
    for person in world.living_persons():
        apply_event(world, Event(
            type=EventType.AGED,
            tick=world.tick,
            scale=TimeScale.POPULATION,
            payload={"person_id": person.id, "delta_years": _YEARS_PER_DAY * elapsed_days},
        ))

    # Estocástico: una sola extracción por persona con la mortalidad acumulada del
    # intervalo, usando la edad ya proyectada. Muestrear, no simular cada día.
    for person in world.living_persons():
        p_daily = _mortality_prob(person.age, person.health)
        p_interval = 1.0 - (1.0 - p_daily) ** elapsed_days
        if rng.random() < p_interval:
            apply_event(world, Event(
                type=EventType.DEATH,
                tick=world.tick,
                scale=TimeScale.POPULATION,
                payload={"person_id": person.id, "age": person.age},
            ))

    # El reloj saltó el intervalo completo.
    apply_event(world, Event(
        type=EventType.TICK,
        tick=world.tick + elapsed_days * 24,
        scale=TimeScale.POPULATION,
        payload={},
    ))

    # ponytail: la proyección cubre demografía (envejecimiento + muerte) y el reloj; no
    # reproyecta economía ni ondas sociales tick a tick — eso depende de decisiones por
    # tick. Upgrade a proyección más profunda es post-MVP (ver ROADMAP "After the MVP").
    return world
