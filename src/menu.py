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
        FONT_PATH = "assets/fonts/PressStart2P-Regular.ttf"
        self.font_title = pygame.font.Font(FONT_PATH, 24)
        self.font_subtitle = pygame.font.Font(FONT_PATH, 14) 
        self.font_btn = pygame.font.Font(FONT_PATH, 12)       
        self.font_small = pygame.font.Font(FONT_PATH, 9)      

        # Cargar e escalar la imagen del título del juego
        try:
            raw_title_img = pygame.image.load("assets/intro/title_logo.png").convert_alpha()
            # Escalar la imagen a un tamaño adecuado para la pantalla del menú
            self.title_img = pygame.transform.scale(raw_title_img, (450, 90))
        except Exception:
            self.title_img = None

        # Cargar e escalar la imagen del arma para los controles
        try:
            raw_gun_img = pygame.image.load("assets/intro/gun.png").convert_alpha()
            # Aumentamos el tamaño de la imagen para que destaque en pantalla
            self.gun_img = pygame.transform.scale(raw_gun_img, (500, 400))
        except Exception as e:
            print(f"Error al cargar la imagen del arma: {e}")
            self.gun_img = None
        
        # Datos de misiones ( Nivel 1 desbloqueado por defecto, 2, 3, 4 bloqueados. )
        self.max_unlocked_mission = 2
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
            # Dibujar la imagen del Título (si no existe, usa texto como fallback)
            if self.title_img:
                rect = self.title_img.get_rect(center=(SCREEN_WIDTH // 2, 110))
                surface.blit(self.title_img, rect)
            else:
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
            # Título principal
            title = self.font_title.render("CONTROLES", True, COLOR_ACCENT)
            surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 60)))

            # 1. DIBUJAR LA IMAGEN MAS GRANDE A LA DERECHA (Puede quedar detrás del texto)
            if self.gun_img:
                gun_rect = self.gun_img.get_rect(center=(SCREEN_WIDTH // 2 + 120, 280))
                surface.blit(self.gun_img, gun_rect)

            # 2. DIBUJAR EL TEXTO DESPLAZADO MÁS HACIA EL CENTRO (x = 120)
            lines = [
                "MOVIMIENTO:",
                "WASD o Flechas",
                "",
                "DIAGONAL:",
                "Soportada (8 dir.)",
                "",
                "PAUSA / SALIR:",
                "Tecla ESC"
            ]
            
            start_y = 140
            for idx, line in enumerate(lines):
                color_linea = COLOR_ACCENT if line.endswith(":") else COLOR_TEXT
                txt = self.font_btn.render(line, True, color_linea)
                # Mover x a 120 para que el texto no quede pegado al borde izquierdo
                surface.blit(txt, (120, start_y + idx * 32))

            self.back_button.draw(surface, mouse_pos)

        

        elif self.state == "CREDITS":
            # Título principal arriba
            title = self.font_title.render("CREDITOS", True, COLOR_ACCENT)
            surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 50)))

            # SECCIÓN: EQUIPO DE DESARROLLO (Bajado a y = 130 para dar aire al título)
            sub_dev = self.font_subtitle.render("--- EQUIPO DE DESARROLLO ---", True, COLOR_ACCENT)
            surface.blit(sub_dev, sub_dev.get_rect(center=(SCREEN_WIDTH // 2, 130)))

            dev1 = self.font_btn.render("Augusto Abel Karacsany", True, COLOR_TEXT)
            dev2 = self.font_btn.render("Lautaro Ezequiel Medina", True, COLOR_TEXT)
            dev3 = self.font_btn.render("Ambar Fiszman Stilveman", True, COLOR_TEXT)
            dev4 = self.font_btn.render("Valentina Artaza", True, COLOR_TEXT)

            # Nombres con mayor tamaño y espaciado de 32px entre cada uno
            surface.blit(dev1, dev1.get_rect(center=(SCREEN_WIDTH // 2, 175)))
            surface.blit(dev2, dev2.get_rect(center=(SCREEN_WIDTH // 2, 207)))
            surface.blit(dev3, dev3.get_rect(center=(SCREEN_WIDTH // 2, 239)))
            surface.blit(dev4, dev4.get_rect(center=(SCREEN_WIDTH // 2, 271)))

            # SECCIÓN: ATRIBUCIONES (Bajado a y = 335)
            sub_attr = self.font_subtitle.render("--- ATRIBUCIONES ESPECIALES ---", True, COLOR_ACCENT)
            surface.blit(sub_attr, sub_attr.get_rect(center=(SCREEN_WIDTH // 2, 335)))

            attr1 = self.font_small.render("Basado en Metal Gear 2: Solid Snake (MSX2)", True, COLOR_TEXT)
            attr2 = self.font_small.render("de Hideo Kojima & Konami", True, COLOR_TEXT)
            surface.blit(attr1, attr1.get_rect(center=(SCREEN_WIDTH // 2, 375)))
            surface.blit(attr2, attr2.get_rect(center=(SCREEN_WIDTH // 2, 395)))

            self.back_button.draw(surface, mouse_pos)

