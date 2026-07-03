"""Vista de Ciudadano (Semana 4).

Vista de solo-lectura: Trabajo · Familia · Transporte. No muta el estado; solo lo
proyecta para el rol. Para el MVP basta con esta única vista.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..state.world import World


@dataclass
class CitizenView:
    """Proyección de solo-lectura del mundo desde la perspectiva de un ciudadano."""

    world: World
    person_id: int

    def summary(self) -> dict:
        person = self.world.persons.get(self.person_id)
        if person is None:
            raise KeyError(f"persona {self.person_id} no existe en el mundo")

        return {
            "person_id": person.id,
            "alive": person.alive,
            "work": self._work(person),
            "family": self._family(person),
            "transport": self._transport(person),
        }

    # --- Secciones (privadas) ------------------------------------------------

    def _work(self, person) -> dict:
        return {
            "employer_id": person.employer_id,
            "employed": person.employer_id is not None,
            "current_action": person.current_action,
            "money": person.money,
        }

    def _family(self, person) -> dict:
        # Convivientes vivos (excluye a la propia persona).
        housemates: list[int] = []
        hh = self.world.households.get(person.household_id) if person.household_id is not None else None
        if hh is not None:
            housemates = [
                mid for mid in hh.member_ids
                if mid != person.id
                and self.world.persons.get(mid) is not None
                and self.world.persons[mid].alive
            ]

        # Vínculos de esta persona: id del otro extremo + fuerza.
        bonds = [
            {"other_id": (rel.b_id if rel.a_id == person.id else rel.a_id), "strength": rel.strength}
            for rel in self.world.relationships.values()
            if person.id in (rel.a_id, rel.b_id)
        ]

        return {
            "household_id": person.household_id,
            "housemates": housemates,
            "bonds": bonds,
        }

    def _transport(self, person) -> dict:
        place = self.world.places.get(person.location_id) if person.location_id is not None else None
        return {
            "location_id": person.location_id,
            "place_type": place.type.value if place is not None else None,
            "at_home": (
                person.household_id is not None
                and self.world.households.get(person.household_id) is not None
                and person.location_id == self.world.households[person.household_id].dwelling_id
            ),
        }
