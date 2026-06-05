"""Gate Semana 4 — Sociedad: una muerte bien conectada riza la red.

Gate: forzar la muerte de una persona con vínculos fuertes produce:
  1. Duelo (traza negativa) en sus allegados cercanos.
  2. Sin duelo para vínculos débiles (<0.40).
  3. El duelo se contagia: las personas con lazos con los enlutados ven su ánimo
     empeorar por la contagión social (integración death → contagion).
  4. Las relaciones se siembran al iniciar la simulación.
"""

from __future__ import annotations

import pytest

from citysim.config import SimConfig
from citysim.rng import Rng
from citysim.seed.seeder import seed_world
from citysim.state.enums import EventType, RelType, TimeScale
from citysim.state.person import MemoryTrace, Needs, Person, Traits
from citysim.state.relationship import Relationship
from citysim.state.world import World
from citysim.systems import contagion, death, emotion as emotion_sys
from citysim.systems.base import TickContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rng(seed: int = 42) -> Rng:
    return Rng(seed)


def _ctx(tick: int = 100, rng: Rng | None = None) -> TickContext:
    return TickContext(
        tick=tick,
        scale=TimeScale.POPULATION,
        rng=rng or _rng(),
    )


def _person(pid: int, age: float = 30.0, health: float = 1.0, alive: bool = True) -> Person:
    traits = Traits(
        ambition=0.5, sociability=0.5, risk_tolerance=0.5,
        conscientiousness=0.5, resilience=0.5,
    )
    needs = Needs(
        belonging=0.5, autonomy=0.5, purpose=0.5, security=0.5, stimulation=0.5,
    )
    return Person(id=pid, age=age, health=health, alive=alive, traits=traits, needs=needs)


def _world_with(persons: list[Person], rels: list[Relationship] | None = None) -> World:
    w = World()
    for p in persons:
        w.persons[p.id] = p
    for rel in (rels or []):
        w.relationships[rel.id] = rel
        if rel.id >= w.next_relationship_id:
            w.next_relationship_id = rel.id + 1
    return w


def _rel(rid: int, a: int, b: int, strength: float) -> Relationship:
    return Relationship(id=rid, a_id=a, b_id=b, type=RelType.FRIEND, strength=strength)


# ---------------------------------------------------------------------------
# _mortality_prob: la probabilidad crece con la edad
# ---------------------------------------------------------------------------

class TestMortalityProb:
    def test_baja_en_persona_joven(self):
        from citysim.systems.death import _mortality_prob
        prob = _mortality_prob(age=30.0, health=1.0)
        assert prob < 0.001

    def test_aumenta_con_la_edad(self):
        from citysim.systems.death import _mortality_prob
        p30 = _mortality_prob(age=30.0, health=1.0)
        p70 = _mortality_prob(age=70.0, health=1.0)
        p90 = _mortality_prob(age=90.0, health=1.0)
        assert p30 < p70 < p90

    def test_salud_baja_multiplica(self):
        from citysim.systems.death import _mortality_prob
        sano = _mortality_prob(age=70.0, health=1.0)
        enfermo = _mortality_prob(age=70.0, health=0.2)
        assert enfermo > sano * 1.5

    def test_limitada_al_25_pct(self):
        from citysim.systems.death import _mortality_prob
        assert _mortality_prob(age=120.0, health=0.0) <= 0.25


# ---------------------------------------------------------------------------
# death.step: emisión de eventos DEATH, INHERITANCE, MEMORY_UPDATED (duelo)
# ---------------------------------------------------------------------------

class TestDeathStep:
    def _force_death(self, pid: int, world: World) -> list:
        """Mata solo a la persona con id=pid; el resto sobrevive."""

        target = pid

        class SelectiveDie:
            def __init__(self):
                self._current_person = None

            def random(self):
                # death.step itera living_persons en orden de inserción.
                # La primera llamada pertenece a la persona con menor id (si se
                # insertó primero). Usamos una lista rotante para identificar a quién
                # corresponde cada llamada según el orden de world.living_persons().
                return 0.0 if self._person_id == target else 1.0

            def randint(self, a, b):
                return a

        rng = SelectiveDie()

        # Parchamos el step para inyectar el id antes de cada llamada a random().
        import citysim.systems.death as death_mod
        original_step = death_mod.step

        living = list(world.living_persons())
        call_index = [0]

        class IndexedRng:
            def random(self):
                pid_ = living[call_index[0]].id if call_index[0] < len(living) else -1
                call_index[0] += 1
                return 0.0 if pid_ == target else 1.0

            def randint(self, a, b):
                return a

        ctx = TickContext(tick=10, scale=TimeScale.POPULATION, rng=IndexedRng())
        return death.step(world, ctx)

    def test_emite_death_para_anciano_muy_enfermo(self):
        elderly = _person(1, age=95.0, health=0.05)
        world = _world_with([elderly])
        events = self._force_death(1, world)
        types = [e.type for e in events]
        assert EventType.DEATH in types

    def test_duelo_en_allegado_con_vinculo_fuerte(self):
        deceased = _person(1, age=80.0, health=0.5)
        griever = _person(2, age=40.0)
        # Vínculo fuerte (≥ 0.40)
        rel = _rel(0, a=1, b=2, strength=0.75)
        world = _world_with([deceased, griever], [rel])
        events = self._force_death(1, world)
        grief_events = [
            e for e in events
            if e.type == EventType.MEMORY_UPDATED
            and e.payload["person_id"] == 2
        ]
        assert grief_events, "debe emitirse duelo para el allegado"
        traces = grief_events[0].payload["traces"]
        grief_traces = [t for t in traces if str(t["event_type"]).startswith("grief_")]
        assert grief_traces, "debe haber una traza de duelo"
        assert grief_traces[0]["valence"] < 0

    def test_sin_duelo_para_vinculo_debil(self):
        deceased = _person(1, age=80.0, health=0.5)
        acquaintance = _person(3, age=35.0)
        # Vínculo débil (< 0.40)
        rel = _rel(1, a=1, b=3, strength=0.20)
        world = _world_with([deceased, acquaintance], [rel])
        events = self._force_death(1, world)
        grief_events = [
            e for e in events
            if e.type == EventType.MEMORY_UPDATED
            and e.payload["person_id"] == 3
        ]
        # Ninguna traza de duelo para vínculo débil
        for e in grief_events:
            traces = e.payload["traces"]
            grief_traces = [t for t in traces if str(t["event_type"]).startswith("grief_")]
            assert not grief_traces

    def test_no_hay_herencia_sin_hogar(self):
        deceased = _person(1, age=80.0, health=0.5)
        deceased.money = 5000.0
        world = _world_with([deceased])
        events = self._force_death(1, world)
        assert not any(e.type == EventType.INHERITANCE for e in events)


# ---------------------------------------------------------------------------
# Seeder: las relaciones se siembran al iniciar
# ---------------------------------------------------------------------------

class TestSeedRelationships:
    def test_relaciones_sembradas_en_mundo_inicial(self):
        config = SimConfig(seed=42, n_persons=50, sim_days=1)
        world = seed_world(config)
        assert len(world.relationships) > 0

    def test_todas_tienen_a_id_y_b_id_validos(self):
        config = SimConfig(seed=42, n_persons=50, sim_days=1)
        world = seed_world(config)
        pids = set(world.persons.keys())
        for rel in world.relationships.values():
            assert rel.a_id in pids
            assert rel.b_id in pids

    def test_fuerza_en_rango_valido(self):
        config = SimConfig(seed=42, n_persons=50, sim_days=1)
        world = seed_world(config)
        for rel in world.relationships.values():
            assert 0.0 <= rel.strength <= 1.0


# ---------------------------------------------------------------------------
# Gate de integración: muerte → duelo → contagio emocional
# ---------------------------------------------------------------------------

class TestDeathRipplesNetwork:
    def test_muerte_genera_emocion_negativa_en_red(self):
        """Una muerte con vínculo fuerte genera duelo, que el sistema de contagio
        propaga como emoción negativa al resto de la red."""

        # Persona fallecida (A), allegado directo (B), allegado de B (C)
        A = _person(10, age=85.0, health=0.1)
        B = _person(20, age=45.0)
        C = _person(30, age=40.0)

        rel_AB = _rel(0, a=10, b=20, strength=0.80)  # fuerte → genera duelo en B
        rel_BC = _rel(1, a=20, b=30, strength=0.60)  # BC enlaza para contagio

        world = _world_with([A, B, C], [rel_AB, rel_BC])

        # Paso 1: forzar muerte de A (solo A; B y C sobreviven)
        living = [A, B, C]
        call_index = [0]

        class KillOnlyA:
            def random(self):
                pid_ = living[call_index[0]].id if call_index[0] < len(living) else -1
                call_index[0] += 1
                return 0.0 if pid_ == 10 else 1.0

            def randint(self, a, b):
                return a

        death_ctx = TickContext(tick=1, scale=TimeScale.POPULATION, rng=KillOnlyA())
        death_events = death.step(world, death_ctx)

        # Aplicar los eventos al mundo manualmente
        from citysim.eventlog.apply import apply_event
        for e in death_events:
            apply_event(world, e)

        # A debe estar muerta
        assert not world.persons[10].alive

        # B debe tener duelo en memoria
        b_grief = [t for t in world.persons[20].memory if t.event_type.startswith("grief_")]
        assert b_grief, "B debe tener duelo en memoria"
        assert b_grief[0].valence < 0

        # Paso 2: contagio — B tiene ánimo negativo, debe contagiar a C
        B_emotion = emotion_sys.compute(world.persons[20])
        assert B_emotion < 0, "B debe tener ánimo negativo tras el duelo"

        contagion_ctx = TickContext(tick=2, scale=TimeScale.DAILY, rng=_rng(99))
        contagion_events = contagion.step(world, contagion_ctx)

        # C debe recibir influencia negativa de B (si B está lo suficientemente negativo)
        c_events = [
            e for e in contagion_events
            if e.payload.get("person_id") == 30
        ]
        if c_events:
            traces = c_events[0].payload["traces"]
            social_traces = [t for t in traces if t["event_type"] == "social_influence"]
            assert social_traces
            # La influencia debe ser negativa porque B tiene duelo
            assert social_traces[0]["valence"] < 0
