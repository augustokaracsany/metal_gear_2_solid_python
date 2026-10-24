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

        # Líneas finas y rectangulares características del iDroid
        pygame.draw.rect(surface, color, self.rect, 1)
        
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
        
        # Fuentes tipográficas del sistema o Pygame
        self.font_title = pygame.font.Font(None, 28)
        self.font_btn = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 16)
        
        self.selected_mission_id = 1

        # Base de datos de misiones con numeración Peace Walker, calaveras de dificultad,
        # mapas TMX reales y tareas (Mission Tasks estilo MGSV)
        self.missions_data = {
            1: {
                "id": "001",
                "title": "ENTRY POINT",
                "difficulty": 2, # Cantidad de calaveras
                "map_file": "assets/maps/mapa_edificio1.tmx", # Ajusta según tu ruta de TMX
                "unlocked": True,
                "objective": "Infiltrarse en la nación fortificada de Zanzibar Land.",
                "situation": "El agente legendario Solid Snake ha sido movilizado de urgencia para rescatar al Dr. Kio Marv, creador del OILIX.",
                "tasks": [
                    "Evitar la alerta antes de entrar a la base.",
                    "Localizar el conducto de ventilación",
                    "Asegurar el acceso al Edificio 1"
                ]
            },
            2: {
                "id": "002",
                "title": "Edificio 1",
                "difficulty": 3,
                "map_file": "assets/maps/mapa_pantano.tmx", # Ajusta según tu ruta de TMX
                "unlocked": True,
                "objective": "Localizar el paradero del Dr. Marv en el edificio.",
                "situation": "El edificio está fuertemente custodiado por fuerzas especiales y cámaras de seguridad.",
                "tasks": [
                    "Evitar la alerta.",
                    "Encontrar la tarjeta de acceso de nivel superior.",
                    "Localizar ak Dr. Kio Marv."
                ]
            },
            3: {
                "id": "003",
                "title": "HIND-D",
                "difficulty": 4,
                "map_file": "assets/sprites/maps/hind-d_boss_fight-576x1344.tmx",
                "unlocked": True,
                "objective": "Destruir el helicóptero de ataque Hind-D.",
                "situation": "Zanzibar Land despliega su arma aérea. Sin cobertura, no hay salida.",
                "tasks": [
                    "Mantenerse con vida bajo el fuego aéreo.",
                    "Usar la cobertura para evitar las ráfagas.",
                    "Derribar el Hind-D."
                ]
            }
        }

        # Botones del Menú Principal
        self.main_buttons = [
            Button("SELECCIÓN DE MISIÓN", SCREEN_WIDTH // 2 - 140, 180, 280, 32, self.font_btn),
            Button("VER CONTROLES", SCREEN_WIDTH // 2 - 140, 230, 280, 32, self.font_btn),
            Button("VER CRÉDITOS", SCREEN_WIDTH // 2 - 140, 280, 280, 32, self.font_btn),
            Button("SALIR DEL JUEGO", SCREEN_WIDTH // 2 - 140, 330, 280, 32, self.font_btn),
        ]

        # Botones de navegación interna
        self.back_button = Button("VOLVER", 40, SCREEN_HEIGHT - 50, 100, 28, self.font_btn)
        self.deploy_button = Button("DESPLEGAR", SCREEN_WIDTH - 280, SCREEN_HEIGHT - 50, 240, 32, self.font_btn)

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
                    self.state = "CREDITS"
                elif self.main_buttons[3].is_clicked(event):
                    return "EXIT"

            elif self.state == "MISSIONS":
                # Comprobar clics en las líneas finas de la columna izquierda de misiones
                for idx, m_data in self.missions_data.items():
                    bx = 40
                    by = 100 + (idx - 1) * 50
                    mission_line_rect = pygame.Rect(bx, by, 360, 38)
                    
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if mission_line_rect.collidepoint(event.pos):
                            self.selected_mission_id = idx

                # Botón de Desplegar (Iniciar Misión seleccionada)
                if self.deploy_button.is_clicked(event):
                    selected_mission = self.missions_data[self.selected_mission_id]
                    if selected_mission["unlocked"]:
                        # Esto matchea perfectamente con tu main.py: action.startswith("START_MISSION_")
                        return f"START_MISSION_{self.selected_mission_id}"
                    
                # Botón Volver al menú principal
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
            # --- CABECERA SUPERIOR (Estilo iDroid MGSV / Peace Walker) ---
            header_text = self.font_title.render("SELECCIÓN DE MISIÓN", True, COLOR_ACCENT)
            surface.blit(header_text, (40, 30))
            pygame.draw.line(surface, COLOR_ACCENT, (40, 65), (SCREEN_WIDTH - 40, 65), 1)

        # COLUMNA IZQUIERDA: LISTA DE MISIONES ( Líneas finas, alargadas, con ID y calaveras )

            for idx, m_data in self.missions_data.items():
                bx = 40
                by = 95 + (idx - 1) * 50
                line_rect = pygame.Rect(bx, by, 360, 40)
                
                is_selected = (self.selected_mission_id == idx)
                is_hovered = line_rect.collidepoint(mouse_pos)

                # Definir colores de la línea fina según selección u hover
                line_color = COLOR_ACCENT if (is_selected or is_hovered) else COLOR_DISABLED
                
                if is_selected:
                    # Fondo sutil para la misión seleccionada activa
                    pygame.draw.rect(surface, (20, 50, 70), line_rect)
                
                # Dibujar rectángulo/línea fina alargada ( Sin bordes gruesos )
                pygame.draw.rect(surface, line_color, line_rect, 1)

                # Texto de la misión en la lista: Número [001] + Nombre
                mission_label = f"[{m_data['id']}] {m_data['title']}"
                txt_surf = self.font_btn.render(mission_label, True, COLOR_TEXT if is_selected else COLOR_DISABLED)
                surface.blit(txt_surf, (bx + 12, by + 10))

            # COLUMNA DERECHA: PANEL DE DETALLES DE LA MISIÓN SELECCIONADA

            selected = self.missions_data[self.selected_mission_id]
            
            rx = 430
            ry = 95
            rw = SCREEN_WIDTH - 470
            rh = SCREEN_HEIGHT - 170

            # Contenedor general derecho con línea fina
            panel_rect = pygame.Rect(rx, ry, rw, rh)
            pygame.draw.rect(surface, COLOR_ACCENT, panel_rect, 1)

            # 1. Nombre de la misión seleccionada arriba del todo en la columna derecha
            r_title = self.font_btn.render(f">> {selected['title']}", True, COLOR_ACCENT)
            surface.blit(r_title, (rx + 20, ry + 15))
            pygame.draw.line(surface, COLOR_ACCENT, (rx + 20, ry + 45), (rx + rw - 20, ry + 45), 1)

            # 2. Objetivo Principal
            obj_label = self.font_small.render("OBJETIVO PRINCIPAL:", True, COLOR_DISABLED)
            surface.blit(obj_label, (rx + 20, ry + 55))
            
            obj_text = self.font_btn.render(selected["objective"], True, COLOR_TEXT)
            surface.blit(obj_text, (rx + 20, ry + 75))

            # 3. Qué está pasando / Explicación de la situación
            sit_label = self.font_small.render("SITUACIÓN", True, COLOR_DISABLED)
            surface.blit(sit_label, (rx + 20, ry + 110))
            
            sit_text = self.font_small.render(selected["situation"], True, COLOR_TEXT)
            surface.blit(sit_text, (rx + 20, ry + 130))

            # 4. Lista de tareas de la misión (Mission Tasks)
            tasks_label = self.font_small.render("TAREAS DE LA MISIÓN:", True, COLOR_DISABLED)
            surface.blit(tasks_label, (rx + 20, ry + 175))

            task_y = ry + 200
            for task in selected["tasks"]:
                # Checkbox fino estilo iDroid
                pygame.draw.rect(surface, COLOR_ACCENT, (rx + 20, task_y + 2, 10, 10), 1)
                t_surf = self.font_small.render(task, True, COLOR_TEXT)
                surface.blit(t_surf, (rx + 40, task_y))
                task_y += 25

            # Botones de control inferiores
            self.back_button.draw(surface, mouse_pos)
            self.deploy_button.draw(surface, mouse_pos)

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
                "Movimiento: WASD o Flechas Direccionales",
                                "Agacharse: Pulsar C",
                                "Cuerpo a Tierra: Pulsar Ctrl",
                                "Acción CQC: Pulsar E",
                                "Pausa / Salir: ESC"
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

