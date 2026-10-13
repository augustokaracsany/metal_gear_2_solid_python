import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BG, COLOR_TEXT, COLOR_ACCENT, COLOR_HOVER, COLOR_DISABLED

class Button:
    def __init__(self, text, x, y, width, height, font):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.is_enabled = True

    def draw(self, surface, mouse_pos):
        color = COLOR_ACCENT if self.is_enabled else COLOR_DISABLED
        if self.is_enabled and self.rect.collidepoint(mouse_pos):
            color = COLOR_HOVER

        # Dibujar recuadro/rectángulo del botón.
        pygame.draw.rect(surface, color, self.rect, 2, border_radius=4)
        
        # Renderizar texto dentro del botón.
        txt_surf = self.font.render(self.text, True, color if self.is_enabled else COLOR_DISABLED)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)

    def is_clicked(self, event):
        if self.is_enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class MenuManager:
    def __init__(self):
        self.state = "MAIN_MENU"  # MAIN_MENU, MISSIONS, CONTROLS, CREDITS, START_GAME, EXIT
        self.font_title = pygame.font.Font(None, 48)
        self.font_btn = pygame.font.Font(None, 32)
        
        # Datos de misiones ( Nivel 1 desbloqueado por defecto, 2, 3, 4 bloqueados. )
        self.max_unlocked_mission = 1 
        self.selected_mission = 1

        # Botones del Menú Principal:
        self.main_buttons = [
            Button("EMPEZAR PARTIDA", SCREEN_WIDTH // 2 - 150, 200, 300, 45, self.font_btn),
            Button("VER CONTROLES", SCREEN_WIDTH // 2 - 150, 260, 300, 45, self.font_btn),
            Button("VER CINEMATICA", SCREEN_WIDTH // 2 - 150, 320, 300, 45, self.font_btn),
            Button("VER CREDITOS", SCREEN_WIDTH // 2 - 150, 380, 300, 45, self.font_btn),
            Button("SALIR DEL JUEGO", SCREEN_WIDTH // 2 - 150, 440, 300, 45, self.font_btn),
        ]

        # Botones de Créditos / Controles ( Volver. ).
        self.back_button = Button("VOLVER", SCREEN_WIDTH // 2 - 100, 480, 200, 40, self.font_btn)

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        action = None

        for event in events:
            if event.type == pygame.QUIT:
                return "EXIT"

            if self.state == "MAIN_MENU":
                if self.main_buttons[0].is_clicked(event):
                    self.state = "MISSIONS"
                elif self.main_buttons[1].is_clicked(event):
                    self.state = "CONTROLS"
                elif self.main_buttons[2].is_clicked(event):
                    return "REPLAY_INTRO"
                elif self.main_buttons[3].is_clicked(event):
                    self.state = "CREDITS"
                elif self.main_buttons[4].is_clicked(event):
                    return "EXIT"

            elif self.state == "MISSIONS":
                # Detectar clics en los niveles ( Ej. 4 recuadros de misiones, agregar más a futuro. ).
                for i in range(1, 5):
                    bx = SCREEN_WIDTH // 2 - 150
                    by = 150 + (i - 1) * 70
                    mission_rect = pygame.Rect(bx, by, 300, 50)
                    
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if mission_rect.collidepoint(event.pos):
                            if i <= self.max_unlocked_mission:
                                self.selected_mission = i
                                return f"START_MISSION_{i}"

                if self.back_button.is_clicked(event):
                    self.state = "MAIN_MENU"

            elif self.state in ["CONTROLS", "CREDITS"]:
                if self.back_button.is_clicked(event):
                    self.state = "MAIN_MENU"

        return action

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill(COLOR_BG)
        mouse_pos = pygame.mouse.get_pos()

        if self.state == "MAIN_MENU":
            # Título del Juego.
            title = self.font_title.render("METAL GEAR 2: SOLID PYTHON", True, COLOR_ACCENT)
            surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 100)))

            for btn in self.main_buttons:
                btn.draw(surface, mouse_pos)

        elif self.state == "MISSIONS":
            title = self.font_title.render("SELECCION DE MISION", True, COLOR_ACCENT)
            surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 80)))

            for i in range(1, 5):
                bx = SCREEN_WIDTH // 2 - 150
                by = 150 + (i - 1) * 70
                rect = pygame.Rect(bx, by, 300, 50)
                
                unlocked = i <= self.max_unlocked_mission
                color = COLOR_ACCENT if unlocked else COLOR_DISABLED
                if unlocked and rect.collidepoint(mouse_pos):
                    color = COLOR_HOVER

                pygame.draw.rect(surface, color, rect, 2, border_radius=4)
                
                status_txt = f"MISION {i}" if unlocked else f"MISION {i} (BLOQUEADA)"
                txt_surf = self.font_btn.render(status_txt, True, color)
                surface.blit(txt_surf, txt_surf.get_rect(center=rect.center))

            self.back_button.draw(surface, mouse_pos)

        elif self.state == "CONTROLS":
            title = self.font_title.render("CONTROLES", True, COLOR_ACCENT)
            surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 100)))

            lines = [
                "Movimiento: WASD o Flechas Direccionales",
                "Diagonal: Soportada (8 direcciones)",
                "Salir de Partida / Pausa: ESC"
            ]
            for idx, line in enumerate(lines):
                txt = self.font_btn.render(line, True, COLOR_TEXT)
                surface.blit(txt, (SCREEN_WIDTH // 2 - 220, 200 + idx * 40))

            self.back_button.draw(surface, mouse_pos)

        elif self.state == "CREDITS":
            title = self.font_title.render("CREDITOS", True, COLOR_ACCENT)
            surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 100)))

            lines = [
                "Desarrollado por:",
                "Augusto Abel Karacsany",
                "Lautaro Ezequiel Medina",
                "Valentina Artaza",
                "Ambar Fiszman",
                "Basado en Metal Gear 2: Solid Snake ( MSX2 ) de Hideo Kojima & Konami"
            ]
            for idx, line in enumerate(lines):
                txt = self.font_btn.render(line, True, COLOR_TEXT)
                surface.blit(txt, txt.get_rect(center=(SCREEN_WIDTH // 2, 220 + idx * 40)))

            self.back_button.draw(surface, mouse_pos)