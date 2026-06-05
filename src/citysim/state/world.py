"""World — contenedor raíz del estado de la simulación.

Mantiene los índices (por id) de todas las entidades y el reloj actual. Es solo datos:
no contiene reglas. Los systems lo leen; solo el eventlog lo muta (ADR-0001, ADR-0003).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .household import Household
from .person import Person
from .place import Place
from .relationship import Relationship


@dataclass
class World:
    """Estado completo del mundo en un instante."""

    tick: int = 0  # tick horario absoluto desde el inicio del run

    persons: dict[int, Person] = field(default_factory=dict)
    households: dict[int, Household] = field(default_factory=dict)
    places: dict[int, Place] = field(default_factory=dict)
    relationships: dict[int, Relationship] = field(default_factory=dict)

    # Contadores de demografía para el invariante de cuadre poblacional.
    born_count: int = 0
    dead_count: int = 0

    # Dinero total al sembrar: baseline del invariante de conservación de dinero (Semana 2).
    initial_money_total: float = 0.0

    # Próximo id disponible para Relationship (Semana 4).
    next_relationship_id: int = 0

    # --- Accesos de conveniencia (lectura) ---

    def living_persons(self) -> list[Person]:
        return [p for p in self.persons.values() if p.alive]

    @property
    def day(self) -> int:
        return self.tick // 24

    @property
    def hour(self) -> int:
        return self.tick % 24
