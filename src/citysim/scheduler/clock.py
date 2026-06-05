"""Scheduler — reloj multi-escala (ADR-0008).

Avanza en ticks horarios y dispara las escalas mayores en sus fronteras. En cada tick
ejecuta los systems registrados para la(s) escala(s) activa(s), filtrados por capa
(ADR-0005) y ordenados por `SystemSpec.order` (ARCHITECTURE.md §5). Los systems solo
emiten eventos; el EventLog es quien aplica (ADR-0001).
"""

from __future__ import annotations

from ..config import SimConfig
from ..eventlog.log import EventLog
from ..rng import Rng
from ..state.enums import EventType, TimeScale
from ..state.event import Event
from ..state.world import World
from ..systems import aging, contagion, death, decision, economy, goals, memory, needs, relations, wellbeing
from ..systems.base import SystemSpec, TickContext


def build_default_registry() -> list[SystemSpec]:
    """Systems disponibles. Solo los de capas activas correrán (filtrado en el Scheduler).

    El scheduler los filtra por escala/capa y los ordena por `SystemSpec.order`, según el
    bucle del agente (ARCHITECTURE.md §5): needs → wellbeing → decision → economía.
    """
    return [
        aging.SPEC,
        needs.SPEC,
        wellbeing.SPEC,
        decision.SPEC,
        economy.SPEC,
        memory.SPEC,
        goals.SPEC,
        relations.SPEC,
        contagion.SPEC,
        death.SPEC,
    ]


# Qué escalas se disparan en una frontera dada del reloj.
def _scales_for(hour: int, day_boundary: bool, month_boundary: bool) -> list[TimeScale]:
    scales = [TimeScale.HOURLY]
    if day_boundary:
        scales.append(TimeScale.DAILY)
        scales.append(TimeScale.POPULATION)  # demografía base: paso diario en el MVP
    if month_boundary:
        scales.append(TimeScale.MONTHLY)
    return scales


class Scheduler:
    def __init__(
        self,
        config: SimConfig,
        registry: list[SystemSpec] | None = None,
    ) -> None:
        self.config = config
        self.registry = registry if registry is not None else build_default_registry()
        self.rng = Rng(config.seed)

    def _active_systems(self, scale: TimeScale) -> list[SystemSpec]:
        specs = [
            s
            for s in self.registry
            if s.scale is scale and self.config.is_active(s.layer)
        ]
        return sorted(specs, key=lambda s: s.order)

    def tick(self, world: World, log: EventLog) -> None:
        """Avanza un tick horario, ejecutando los systems de las escalas que correspondan."""
        next_tick = world.tick + 1
        hour = next_tick % 24
        day_boundary = hour == 0
        month_boundary = day_boundary and (next_tick // 24) % 30 == 0

        # Evento de reloj primero: fija world.tick de forma auditable.
        log.commit(world, [Event(type=EventType.TICK, tick=next_tick, scale=TimeScale.HOURLY)])

        for scale in _scales_for(hour, day_boundary, month_boundary):
            for spec in self._active_systems(scale):
                ctx = TickContext(tick=next_tick, scale=scale, rng=self.rng.derive(f"{spec.name}_{next_tick}"))
                events = spec.fn(world, ctx)
                log.commit(world, events)

    def run(self, world: World, log: EventLog, days: int | None = None) -> None:
        """Corre `days` días (por defecto, los del config) en ticks horarios."""
        total_ticks = (days if days is not None else self.config.sim_days) * 24
        for _ in range(total_ticks):
            self.tick(world, log)
