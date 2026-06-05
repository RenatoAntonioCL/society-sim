"""view — la capa Pygame del cliente (ADR-0011).

Solo presentación: dibuja lo que el `SimController` expone y le manda eventos de input.
Sin lógica de simulación, sin mutar estado. Pygame se importa **aquí** (nunca en
`controller`/`layout`), de modo que el resto del cliente funciona y se testea sin display.
"""

from __future__ import annotations

import pygame

from . import layout
from .controller import SCREEN_CREATE, SCREEN_WORLD, SimController
from .paths import default_save_path

WIDTH, HEIGHT = 1100, 720
PANEL_W = 320          # ancho del panel de eventos (derecha)
BAR_H = 64             # alto de la barra de controles (abajo)
FPS = 60


def _load_font(size: int) -> "pygame.font.Font":
    """Fuente integrada de Pygame (freesansbold).

    Se prefiere a `SysFont` porque viaja con Pygame: en un ejecutable congelado
    (PyInstaller) no depende de que el SO tenga una fuente concreta instalada (ADR-0013).
    """
    return pygame.font.Font(None, size)

# Paleta sobria.
BG = (18, 20, 28)
PANEL_BG = (26, 29, 40)
INK = (228, 231, 240)
MUTED = (140, 146, 162)
ACCENT = (90, 160, 250)
OK = (90, 200, 140)
WARN = (235, 170, 80)
FIELD_BG = (38, 42, 56)
FIELD_ACTIVE = (54, 60, 80)

PLACE_COLORS = {
    "home": (90, 130, 200),
    "business": (210, 160, 70),
    "school": (160, 120, 210),
    "hospital": (220, 100, 110),
    "shop": (90, 200, 140),
    "park": (110, 190, 120),
}

PLACE_LABELS = {
    "home":     "Casa",
    "business": "Emp.",
    "school":   "Esc.",
    "hospital": "Hosp.",
    "shop":     "Tienda",
    "park":     "Parque",
}

ACTION_COLORS = {
    "work":      (235, 190,  60),   # amarillo — trabajando
    "socialize": (180, 110, 230),   # violeta  — socializando
    "rest":      ( 80, 140, 220),   # azul     — descansando
    "consume":   ( 90, 200, 140),   # verde    — consumiendo
}


class Button:
    def __init__(self, rect: tuple[int, int, int, int], label: str, action) -> None:
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action

    def draw(self, surf, font) -> None:
        pygame.draw.rect(surf, FIELD_BG, self.rect, border_radius=6)
        pygame.draw.rect(surf, MUTED, self.rect, width=1, border_radius=6)
        txt = font.render(self.label, True, INK)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def handle(self, pos) -> bool:
        if self.rect.collidepoint(pos):
            self.action()
            return True
        return False


class TextField:
    def __init__(self, rect, label: str, value: str) -> None:
        self.rect = pygame.Rect(rect)
        self.label = label
        self.value = value
        self.active = False

    def draw(self, surf, font, small) -> None:
        lbl = small.render(self.label, True, MUTED)
        surf.blit(lbl, (self.rect.x, self.rect.y - 20))
        bg = FIELD_ACTIVE if self.active else FIELD_BG
        pygame.draw.rect(surf, bg, self.rect, border_radius=6)
        border = ACCENT if self.active else MUTED
        pygame.draw.rect(surf, border, self.rect, width=1, border_radius=6)
        txt = font.render(self.value or "0", True, INK)
        surf.blit(txt, (self.rect.x + 10, self.rect.y + 8))

    def handle_key(self, event) -> None:
        if event.key == pygame.K_BACKSPACE:
            self.value = self.value[:-1]
        elif event.unicode.isdigit():
            self.value = (self.value + event.unicode)[:7]

    def as_int(self, default: int) -> int:
        return int(self.value) if self.value.isdigit() and int(self.value) > 0 else default


class App:
    def __init__(self, controller: SimController | None = None) -> None:
        pygame.init()
        pygame.display.set_caption("Simulación urbana — cliente de escritorio")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        # Fuente integrada de Pygame; tamaños ajustados a su métrica (≈ alto en píxeles).
        self.font = _load_font(22)
        self.big = _load_font(38)
        self.small = _load_font(18)
        self.ctrl = controller or SimController()
        self.save_path = default_save_path()
        self.running = True

        # --- Cámara: zoom y desplazamiento del lienzo del mundo ---
        self._cam_offset: list[float] = [0.0, 0.0]
        self._cam_scale: float = 1.0
        self._pan_last: tuple[int, int] | None = None

        # Campos de la pantalla de creación.
        cx = WIDTH // 2 - 140
        self.fields = [
            TextField((cx, 230, 280, 36), "Semilla (seed)", "42"),
            TextField((cx, 300, 280, 36), "Personas", "100"),
            TextField((cx, 370, 280, 36), "Hogares", "30"),
            TextField((cx, 440, 280, 36), "Empresas", "20"),
        ]
        self.create_btn = Button((cx, 500, 135, 40), "Crear mundo", self._do_create)
        self.load_btn = Button((cx + 145, 500, 135, 40), "Cargar", self._do_load)
        self._world_buttons: list[Button] = []

    # --- Acciones ------------------------------------------------------------

    def _do_create(self) -> None:
        self.ctrl.create_world(
            seed=self.fields[0].as_int(42),
            n_persons=self.fields[1].as_int(100),
            n_households=self.fields[2].as_int(30),
            n_businesses=self.fields[3].as_int(20),
        )
        self._reset_camera()

    def _do_load(self) -> None:
        if self.save_path.exists():
            self.ctrl.load(self.save_path)
            self._reset_camera()

    def _do_save(self) -> None:
        self.ctrl.save(self.save_path)

    def _build_world_buttons(self) -> None:
        y = HEIGHT - BAR_H + 12
        self._world_buttons = [
            Button((16, y, 110, 40), "Play/Pausa", self.ctrl.toggle_play),
            Button((134, y, 70, 40), "Paso", self.ctrl.step),
            Button((212, y, 50, 40), "<<", self.ctrl.slower),
            Button((270, y, 50, 40), ">>", self.ctrl.faster),
            Button((328, y, 90, 40), "Guardar", self._do_save),
            Button((426, y, 90, 40), "Cargar", self._do_load),
        ]

    # --- Loop ----------------------------------------------------------------

    def run(self) -> None:
        self._build_world_buttons()
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            if self.ctrl.screen == SCREEN_WORLD:
                self.ctrl.update(dt)
            self._draw()
            pygame.display.flip()
        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEWHEEL:
                if self.ctrl.screen == SCREEN_WORLD:
                    mx, my = pygame.mouse.get_pos()
                    factor = 1.15 if event.y > 0 else 1.0 / 1.15
                    self._zoom(mx, my, factor)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self._handle_click(event.pos)
                elif event.button in (2, 3) and self.ctrl.screen == SCREEN_WORLD:
                    self._pan_last = event.pos
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (2, 3):
                    self._pan_last = None
            elif event.type == pygame.MOUSEMOTION:
                if self._pan_last is not None:
                    dx = event.pos[0] - self._pan_last[0]
                    dy = event.pos[1] - self._pan_last[1]
                    self._cam_offset[0] += dx
                    self._cam_offset[1] += dy
                    self._pan_last = event.pos
            elif event.type == pygame.KEYDOWN:
                self._handle_key(event)

    def _handle_click(self, pos) -> None:
        if self.ctrl.screen == SCREEN_CREATE:
            for f in self.fields:
                f.active = f.rect.collidepoint(pos)
            self.create_btn.handle(pos)
            self.load_btn.handle(pos)
        else:
            for b in self._world_buttons:
                if b.handle(pos):
                    return
            self._select_person_at(pos)

    def _select_person_at(self, pos) -> None:
        """Selecciona la persona bajo el clic; en vacío del lienzo, deselecciona.

        Los clics sobre el panel o la barra no tocan la selección (así se puede mirar
        el panel sin perderla). La geometría se deriva igual que al dibujar.
        """
        state = self.ctrl.world_state()
        if state is None:
            return
        x, y = pos
        canvas_w = WIDTH - PANEL_W
        canvas_h = HEIGHT - BAR_H
        if x >= canvas_w or y >= canvas_h:
            return
        # Invertir transformada de cámara para obtener coords del lienzo.
        wx, wy = self._s2w(float(x), float(y))
        place_pos = layout.place_positions(state.places, canvas_w, canvas_h)
        self.ctrl.select(layout.person_at((wx, wy), state.persons, place_pos))

    def _handle_key(self, event) -> None:
        if self.ctrl.screen == SCREEN_CREATE:
            for f in self.fields:
                if f.active:
                    f.handle_key(event)
            return
        # Pantalla del mundo: atajos.
        if event.key == pygame.K_SPACE:
            self.ctrl.toggle_play()
        elif event.key == pygame.K_RIGHT:
            self.ctrl.step()
        elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
            self.ctrl.faster()
        elif event.key == pygame.K_MINUS:
            self.ctrl.slower()
        elif event.key == pygame.K_s:
            self._do_save()
        elif event.key == pygame.K_l:
            self._do_load()
        elif event.key == pygame.K_ESCAPE:
            self.ctrl.select(None)
        elif event.key == pygame.K_h:
            self._reset_camera()

    # --- Cámara --------------------------------------------------------------

    def _w2s(self, x: float, y: float) -> tuple[int, int]:
        """Coordenadas del lienzo → pantalla (aplica zoom y desplazamiento)."""
        return (
            int(x * self._cam_scale + self._cam_offset[0]),
            int(y * self._cam_scale + self._cam_offset[1]),
        )

    def _s2w(self, x: float, y: float) -> tuple[float, float]:
        """Coordenadas de pantalla → lienzo (inversa de la cámara)."""
        return (
            (x - self._cam_offset[0]) / self._cam_scale,
            (y - self._cam_offset[1]) / self._cam_scale,
        )

    def _zoom(self, mx: int, my: int, factor: float) -> None:
        """Aplica zoom centrado en el cursor (mx, my) en coords de pantalla."""
        new_scale = max(0.2, min(8.0, self._cam_scale * factor))
        f = new_scale / self._cam_scale
        self._cam_scale = new_scale
        self._cam_offset[0] = mx + (self._cam_offset[0] - mx) * f
        self._cam_offset[1] = my + (self._cam_offset[1] - my) * f

    def _reset_camera(self) -> None:
        self._cam_offset[0] = 0.0
        self._cam_offset[1] = 0.0
        self._cam_scale = 1.0

    # --- Dibujo --------------------------------------------------------------

    def _draw(self) -> None:
        self.screen.fill(BG)
        if self.ctrl.screen == SCREEN_CREATE:
            self._draw_create()
        else:
            self._draw_world()

    def _draw_create(self) -> None:
        title = self.big.render("Crear un mundo", True, INK)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 150))
        hint = self.small.render(
            "El mismo seed + config produce siempre el mismo mundo (determinista).",
            True, MUTED,
        )
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 190))
        for f in self.fields:
            f.draw(self.screen, self.font, self.small)
        self.create_btn.draw(self.screen, self.font)
        self.load_btn.draw(self.screen, self.font)

    def _draw_world(self) -> None:
        state = self.ctrl.world_state()
        if state is None:
            return
        canvas_w = WIDTH - PANEL_W
        canvas_h = HEIGHT - BAR_H

        # Acotar el dibujo al lienzo para que los elementos no invadan el panel.
        self.screen.set_clip(pygame.Rect(0, 0, canvas_w, canvas_h))

        place_pos = layout.place_positions(state.places, canvas_w, canvas_h)
        # Etiqueta solo visible a partir de cierto zoom para no saturar la vista alejada.
        show_labels = self._cam_scale >= 0.6
        for place in state.places:
            wx, wy = place_pos[place.id]
            sx, sy = self._w2s(wx, wy)
            color = PLACE_COLORS.get(place.type, MUTED)
            pygame.draw.rect(self.screen, color, pygame.Rect(sx - 9, sy - 9, 18, 18), border_radius=3)
            if show_labels:
                prefix = PLACE_LABELS.get(place.type, place.type)
                lbl = self.small.render(f"{prefix} {place.id}", True, color)
                self.screen.blit(lbl, (sx - lbl.get_width() // 2, sy + 11))
        for person in state.persons:
            wx, wy = layout.person_position(person, place_pos)
            sx, sy = self._w2s(wx, wy)
            if person.alive:
                color = ACTION_COLORS.get(person.current_action or "", MUTED)
            else:
                color = (70, 70, 80)
            pygame.draw.circle(self.screen, color, (sx, sy), 3)

        self.screen.set_clip(None)

        self._draw_legend()

        # Resalta e inspecciona a la persona seleccionada (si hay).
        selected = self.ctrl.selected_person()
        if selected is not None:
            wx, wy = layout.person_position(selected, place_pos)
            sx, sy = self._w2s(wx, wy)
            if 0 <= sx < canvas_w and 0 <= sy < canvas_h:
                pygame.draw.circle(self.screen, ACCENT, (sx, sy), 9, width=2)
            self._draw_person_panel(selected, canvas_w)
        else:
            self._draw_event_panel(state, canvas_w)
        self._draw_bar(state)

    def _meter_color(self, v: float):
        """Color de la barra por nivel: bajo (cálido) → medio → alto (verde)."""
        if v < 0.34:
            return WARN
        return ACCENT if v < 0.67 else OK

    def _section(self, x: int, y: int, title: str) -> int:
        txt = self.small.render(title.upper(), True, ACCENT)
        self.screen.blit(txt, (x, y))
        return y + 22

    def _meter(self, x: int, y: int, w: int, label: str, value: float) -> int:
        """Dibuja `label`, su valor [0,1] y una barra. Devuelve el `y` de la fila siguiente."""
        self.screen.blit(self.small.render(label, True, MUTED), (x, y))
        self.screen.blit(self.small.render(f"{value:.2f}", True, INK), (x + w + 6, y))
        track = pygame.Rect(x, y + 16, w, 7)
        pygame.draw.rect(self.screen, FIELD_BG, track, border_radius=4)
        v = max(0.0, min(1.0, value))
        fill = int(w * v)
        if fill > 0:
            pygame.draw.rect(
                self.screen, self._meter_color(v), pygame.Rect(x, y + 16, fill, 7), border_radius=4
            )
        return y + 27

    def _emotion_meter(self, x: int, y: int, w: int, value: float) -> int:
        """Medidor bipolar de ánimo [-1,1]: rojo a la izquierda (malestar), verde a la
        derecha (bienestar), con marca de centro en 0."""
        mood = "malestar" if value < -0.15 else ("bienestar" if value > 0.15 else "neutro")
        self.screen.blit(self.small.render("Ánimo", True, MUTED), (x, y))
        self.screen.blit(self.small.render(f"{value:+.2f}  {mood}", True, INK), (x + 60, y))
        bar_y = y + 16
        pygame.draw.rect(self.screen, FIELD_BG, pygame.Rect(x, bar_y, w, 7), border_radius=4)
        cx = x + w // 2
        v = max(-1.0, min(1.0, value))
        half = int((w // 2) * abs(v))
        if half > 0:
            rect = pygame.Rect(cx - half, bar_y, half, 7) if v < 0 else pygame.Rect(cx, bar_y, half, 7)
            pygame.draw.rect(self.screen, WARN if v < 0 else OK, rect, border_radius=4)
        pygame.draw.line(self.screen, MUTED, (cx, bar_y - 2), (cx, bar_y + 9))
        return y + 30

    def _draw_person_panel(self, person, canvas_w: int) -> None:
        pygame.draw.rect(self.screen, PANEL_BG, pygame.Rect(canvas_w, 0, PANEL_W, HEIGHT - BAR_H))
        x = canvas_w + 16
        w = PANEL_W - 32 - 44  # ancho de barra; deja sitio al valor a la derecha

        status = "viva" if person.alive else "†"
        self.screen.blit(self.font.render(f"Persona #{person.id}  ({status})", True, INK), (x, 14))
        action = person.current_action or "—"
        self.screen.blit(self.small.render(f"edad {person.age:.0f}  ·  {action}", True, MUTED), (x, 44))
        money_col = OK if person.money >= 0 else WARN
        self.screen.blit(self.small.render(f"$ {person.money:,.0f}", True, money_col), (x, 64))

        y = self._emotion_meter(x, 88, w, person.emotion)

        y = self._section(x, y, "Estado")
        y = self._meter(x, y, w, "Bienestar", person.wellbeing)
        y = self._meter(x, y, w, "Salud", person.health)
        y = self._meter(x, y, w, "Energía", person.energy)

        y = self._section(x, y + 8, "Rasgos")
        t = person.traits
        for label, val in (
            ("Sociabilidad", t.sociability),
            ("Ambición", t.ambition),
            ("Tol. al riesgo", t.risk_tolerance),
            ("Escrupulosidad", t.conscientiousness),
            ("Resiliencia", t.resilience),
        ):
            y = self._meter(x, y, w, label, val)

        y = self._section(x, y + 8, "Necesidades")
        n = person.needs
        for label, val in (
            ("Pertenencia", n.belonging),
            ("Autonomía", n.autonomy),
            ("Propósito", n.purpose),
            ("Seguridad", n.security),
            ("Estimulación", n.stimulation),
        ):
            y = self._meter(x, y, w, label, val)

        y = self._section(x, y + 8, "Objetivos")
        active_goals = [g for g in person.goals if g.active]
        if active_goals:
            for g in active_goals[:3]:
                pct = max(0.0, min(1.0, g.progress))
                self.screen.blit(self.small.render(g.kind, True, INK), (x, y))
                self.screen.blit(self.small.render(f"{int(pct * 100)}%", True, MUTED), (x + w + 6, y))
                pygame.draw.rect(self.screen, FIELD_BG, pygame.Rect(x, y + 15, w, 5), border_radius=3)
                fill = int(w * pct)
                if fill > 0:
                    pygame.draw.rect(self.screen, ACCENT, pygame.Rect(x, y + 15, fill, 5), border_radius=3)
                y += 26
        else:
            self.screen.blit(self.small.render("sin objetivos activos", True, MUTED), (x, y))

        hint = self.small.render("ESC o clic en vacío: cerrar", True, MUTED)
        self.screen.blit(hint, (x, HEIGHT - BAR_H - 24))

    def _draw_legend(self) -> None:
        """Leyenda de colores de acción, esquina inferior izquierda del lienzo."""
        labels = [
            ("trabajo",     ACTION_COLORS["work"]),
            ("socializar",  ACTION_COLORS["socialize"]),
            ("descanso",    ACTION_COLORS["rest"]),
            ("consumo",     ACTION_COLORS["consume"]),
        ]
        x0 = 10
        y0 = HEIGHT - BAR_H - 14 - len(labels) * 16
        for label, color in labels:
            pygame.draw.circle(self.screen, color, (x0 + 5, y0 + 6), 5)
            self.screen.blit(self.small.render(label, True, MUTED), (x0 + 14, y0 - 1))
            y0 += 16

    def _draw_event_panel(self, state, canvas_w: int) -> None:
        panel = pygame.Rect(canvas_w, 0, PANEL_W, HEIGHT - BAR_H)
        pygame.draw.rect(self.screen, PANEL_BG, panel)
        head = self.font.render("Eventos recientes", True, INK)
        self.screen.blit(head, (canvas_w + 16, 14))
        y = 46
        for e in self.ctrl.recent_events(16):
            line = f"t{e.tick:<5} {e.type}"
            txt = self.small.render(line[:40], True, MUTED)
            self.screen.blit(txt, (canvas_w + 16, y))
            y += 18
            if y > HEIGHT - BAR_H - 20:
                break

    def _draw_bar(self, state) -> None:
        bar = pygame.Rect(0, HEIGHT - BAR_H, WIDTH, BAR_H)
        pygame.draw.rect(self.screen, PANEL_BG, bar)
        for b in self._world_buttons:
            b.draw(self.screen, self.font)

        tick, day, hour = self.ctrl.clock
        play = "▶" if self.ctrl.playing else "❚❚"
        hud = (
            f"{play}  día {day:>3}  {hour:02d}:00   "
            f"vivos {state.n_persons_alive:>3}   "
            f"$ {self.ctrl.total_money():>10,.0f}   "
            f"vel {self.ctrl.speed}/s"
        )
        txt = self.font.render(hud, True, INK)
        self.screen.blit(txt, (540, HEIGHT - BAR_H + 22))


def main() -> None:
    App().run()


def run_smoke(ticks: int = 48) -> None:
    """Arranque de validación, sin interacción: crea un mundo, avanza y dibuja un frame.

    Pensado para correr el ejecutable congelado con `--smoke` (SDL en modo dummy) y
    confirmar que el bundle realmente inicia, sin necesidad de pantalla (ADR-0013).
    """
    app = App()
    app.ctrl.create_world(seed=42, n_persons=60, n_households=15, n_businesses=8)
    app.ctrl.toggle_play()
    app.ctrl.set_speed(24)
    app._build_world_buttons()
    for _ in range(5):
        app.ctrl.update(ticks / (5 * app.ctrl.speed))
        app._draw()
    pygame.quit()
