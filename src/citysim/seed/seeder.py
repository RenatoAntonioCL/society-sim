"""Seeder — construye la población inicial de forma determinista.

Escala MVP: 100 personas · 30 hogares · 20 empresas · 1 barrio. Toda la aleatoriedad
sale del RNG sembrado (ADR-0002): mismo seed ⇒ misma población.

Semana 1 genera estado base (sin rasgos). Los rasgos y necesidades se incorporan en la
Semana 2 (con variación poblacional y herencia parcial).
"""

from __future__ import annotations

from ..config import SimConfig
from ..rng import Rng
from ..state.enums import PlaceType, RelType
from ..state.household import Household
from ..state.person import Person, Traits
from ..state.place import Place
from ..state.relationship import Relationship
from ..state.world import World
from ..systems.base import clamp01

# Edad laboral para la economía mínima (Semana 2).
_WORK_AGE_MIN = 18.0
_WORK_AGE_MAX = 65.0


def _sample_traits(rng: Rng) -> Traits:
    """Rasgos con variación poblacional (ADR-0006): centrados en 0.5, con dispersión.

    Se muestrean del RNG sembrado, no fijos. La herencia parcial de progenitores queda
    fuera de alcance hasta que exista un modelo de parentesco.
    """
    return Traits(
        sociability=clamp01(rng.gauss(0.5, 0.18)),
        ambition=clamp01(rng.gauss(0.5, 0.18)),
        risk_tolerance=clamp01(rng.gauss(0.5, 0.18)),
        conscientiousness=clamp01(rng.gauss(0.5, 0.18)),
        resilience=clamp01(rng.gauss(0.5, 0.18)),
    )


def seed_world(config: SimConfig) -> World:
    """Devuelve un World poblado de forma determinista a partir del config."""
    world = World()
    rng = Rng(config.seed).derive("seeder")
    traits_rng = Rng(config.seed).derive("traits")

    # --- Lugares: 1 barrio, viviendas y empresas ---
    next_place_id = 0
    for _ in range(config.n_households):
        world.places[next_place_id] = Place(
            id=next_place_id, type=PlaceType.HOME, capacity=6, location_id=0
        )
        next_place_id += 1
    for _ in range(config.n_businesses):
        world.places[next_place_id] = Place(
            id=next_place_id, type=PlaceType.BUSINESS, capacity=20, location_id=0,
            open_hour=8, close_hour=18,
        )
        next_place_id += 1

    home_ids = [p.id for p in world.places.values() if p.type is PlaceType.HOME]

    # --- Personas ---
    for pid in range(config.n_persons):
        world.persons[pid] = Person(
            id=pid,
            age=rng.uniform(0, 80),
            money=rng.uniform(0, 5000),
            energy=rng.uniform(0.5, 1.0),
            wellbeing=0.5,
            health=rng.uniform(0.7, 1.0),
            traits=_sample_traits(traits_rng),
        )
        world.born_count += 1

    # Baseline para el invariante de conservación de dinero (Semana 2).
    world.initial_money_total = sum(p.money for p in world.persons.values())

    # --- Hogares: repartir personas en hogares ---
    person_ids = list(world.persons.keys())
    rng.shuffle(person_ids)
    for hid in range(config.n_households):
        world.households[hid] = Household(id=hid, dwelling_id=home_ids[hid], location_id=0)

    for i, pid in enumerate(person_ids):
        hid = i % config.n_households
        world.households[hid].member_ids.append(pid)
        world.persons[pid].household_id = hid
        world.persons[pid].location_id = world.households[hid].dwelling_id

    # --- Empleo: personas en edad laboral a empresas, respetando capacidad ---
    business_ids = [p.id for p in world.places.values() if p.type is PlaceType.BUSINESS]
    if business_ids:
        slots = {bid: world.places[bid].capacity for bid in business_ids}
        b = 0
        for pid in person_ids:
            person = world.persons[pid]
            if not (_WORK_AGE_MIN <= person.age < _WORK_AGE_MAX):
                continue
            # Busca la próxima empresa con cupo (round-robin determinista).
            for _ in range(len(business_ids)):
                bid = business_ids[b % len(business_ids)]
                b += 1
                if slots[bid] > 0:
                    person.employer_id = bid
                    slots[bid] -= 1
                    break

    # --- Relaciones iniciales (Semana 4) ---
    rel_rng = Rng(config.seed).derive("seeder_relations")
    rel_id = 0

    # Familia: todos los pares dentro de cada hogar (vínculo fuerte)
    for hh in world.households.values():
        members = hh.member_ids
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                world.relationships[rel_id] = Relationship(
                    id=rel_id,
                    a_id=members[i],
                    b_id=members[j],
                    type=RelType.FAMILY,
                    strength=rel_rng.uniform(0.65, 0.95),
                    reciprocity=rel_rng.uniform(0.70, 1.00),
                )
                rel_id += 1

    # Trabajo: pares de colegas en la misma empresa (vínculo moderado, round-robin)
    employees_by_biz: dict[int, list[int]] = {}
    for pid, person in world.persons.items():
        if person.employer_id is not None:
            employees_by_biz.setdefault(person.employer_id, []).append(pid)
    for emps in employees_by_biz.values():
        shuffled = list(emps)
        rel_rng.shuffle(shuffled)
        for i in range(0, len(shuffled) - 1, 2):
            world.relationships[rel_id] = Relationship(
                id=rel_id,
                a_id=shuffled[i],
                b_id=shuffled[i + 1],
                type=RelType.WORK,
                strength=rel_rng.uniform(0.30, 0.55),
                reciprocity=rel_rng.uniform(0.40, 0.70),
            )
            rel_id += 1

    # Amistades aleatorias (vínculo débil/moderado, hasta 80 pares únicos)
    existing_pairs: set[tuple[int, int]] = {
        (min(r.a_id, r.b_id), max(r.a_id, r.b_id))
        for r in world.relationships.values()
    }
    pid_list = list(world.persons.keys())
    for _ in range(80):
        a_id = rel_rng.choice(pid_list)
        b_id = rel_rng.choice(pid_list)
        if a_id == b_id:
            continue
        pair = (min(a_id, b_id), max(a_id, b_id))
        if pair in existing_pairs:
            continue
        world.relationships[rel_id] = Relationship(
            id=rel_id,
            a_id=a_id,
            b_id=b_id,
            type=RelType.FRIEND,
            strength=rel_rng.uniform(0.20, 0.55),
            reciprocity=rel_rng.uniform(0.30, 0.65),
        )
        existing_pairs.add(pair)
        rel_id += 1

    world.next_relationship_id = rel_id

    return world
