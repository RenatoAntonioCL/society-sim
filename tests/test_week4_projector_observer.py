"""Semana 4 — proyección offline y vista de Ciudadano.

Projector: separa lo determinista (envejecer, reloj) de lo estocástico (muerte,
muestreada una vez sobre el intervalo). Observer: proyección de solo-lectura del mundo
para un ciudadano (Trabajo · Familia · Transporte).
"""

from __future__ import annotations

import pytest

from citysim.observers.citizen import CitizenView
from citysim.projector.projector import project_forward
from citysim.state.enums import PlaceType, RelType
from citysim.state.household import Household
from citysim.state.person import Person
from citysim.state.place import Place
from citysim.state.relationship import Relationship
from citysim.state.world import World


class _FixedRng:
    """rng determinista para el test: random() devuelve un valor fijo."""

    def __init__(self, value: float) -> None:
        self._value = value

    def random(self) -> float:
        return self._value

    def randint(self, a: int, b: int) -> int:
        return a


def _person(pid: int, **kw) -> Person:
    return Person(id=pid, **kw)


def _world(persons: list[Person]) -> World:
    w = World()
    for p in persons:
        w.persons[p.id] = p
    return w


# --- Projector --------------------------------------------------------------

class TestProjector:
    def test_envejece_en_un_salto(self):
        w = _world([_person(1, age=30.0, health=1.0)])
        project_forward(w, elapsed_days=365, rng=_FixedRng(0.99))
        assert w.persons[1].age == pytest.approx(31.0)

    def test_avanza_el_reloj_el_intervalo_completo(self):
        w = _world([_person(1, age=30.0)])
        w.tick = 100
        project_forward(w, elapsed_days=10, rng=_FixedRng(0.99))
        assert w.tick == 100 + 10 * 24

    def test_muerte_muestreada_mata_al_anciano_enfermo(self):
        # rng.random()=0.0 < cualquier p_interval > 0 → muere.
        w = _world([_person(1, age=95.0, health=0.05)])
        project_forward(w, elapsed_days=365, rng=_FixedRng(0.0))
        assert not w.persons[1].alive
        assert w.dead_count == 1

    def test_joven_sano_sobrevive_con_rng_alto(self):
        w = _world([_person(1, age=25.0, health=1.0)])
        project_forward(w, elapsed_days=365, rng=_FixedRng(0.99))
        assert w.persons[1].alive

    def test_cero_dias_es_no_op(self):
        w = _world([_person(1, age=30.0)])
        before = w.persons[1].age
        project_forward(w, elapsed_days=0, rng=_FixedRng(0.0))
        assert w.persons[1].age == before

    def test_dias_negativos_falla(self):
        w = _world([_person(1)])
        with pytest.raises(ValueError):
            project_forward(w, elapsed_days=-1, rng=_FixedRng(0.0))


# --- Observer ---------------------------------------------------------------

class TestCitizenView:
    def _seed(self) -> World:
        alice = _person(1, employer_id=99, current_action="work", money=500.0,
                        household_id=10, location_id=99)
        bob = _person(2, household_id=10, location_id=77)      # conviviente vivo
        carol = _person(3, alive=False, household_id=10)       # conviviente muerto
        w = _world([alice, bob, carol])
        w.households[10] = Household(id=10, member_ids=[1, 2, 3], dwelling_id=77)
        w.places[99] = Place(id=99, type=PlaceType.BUSINESS)
        w.relationships[0] = Relationship(id=0, a_id=1, b_id=2, type=RelType.FRIEND, strength=0.8)
        return w

    def test_secciones_presentes(self):
        view = CitizenView(self._seed(), person_id=1)
        s = view.summary()
        assert set(s["work"]) >= {"employed", "current_action", "money"}
        assert "housemates" in s["family"]
        assert "location_id" in s["transport"]

    def test_trabajo_refleja_empleo(self):
        s = CitizenView(self._seed(), person_id=1).summary()
        assert s["work"]["employed"] is True
        assert s["work"]["money"] == 500.0

    def test_convivientes_excluyen_a_si_mismo_y_a_los_muertos(self):
        s = CitizenView(self._seed(), person_id=1).summary()
        assert s["family"]["housemates"] == [2]  # ni 1 (uno mismo) ni 3 (muerto)

    def test_bonds_listan_el_otro_extremo(self):
        s = CitizenView(self._seed(), person_id=1).summary()
        assert s["family"]["bonds"] == [{"other_id": 2, "strength": 0.8}]

    def test_transporte_marca_en_el_trabajo(self):
        s = CitizenView(self._seed(), person_id=1).summary()
        assert s["transport"]["place_type"] == PlaceType.BUSINESS.value
        assert s["transport"]["at_home"] is False

    def test_persona_inexistente_falla(self):
        with pytest.raises(KeyError):
            CitizenView(self._seed(), person_id=999).summary()
