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
        # Estados posibles: MAIN_MENU, MISSIONS, CONTROLS, CREDITS, EXIT
        self.state = "MAIN_MENU"  
        
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
            # Título principal del juego
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
            title = self.font_title.render("CONTROLES", True, COLOR_ACCENT)
            surface.blit(title, (40, 40))

            controls_lines = [
                "Movimiento: WASD o Flechas Direccionales",
                "Agacharse: Pulsar C",
                "Cuerpo a Tierra: Pulsar Ctrl",
                "Acción CQC: Pulsar E",
                "Pausa / Salir: ESC"
            ]
            for idx, line in enumerate(controls_lines):
                txt = self.font_btn.render(line, True, COLOR_TEXT)
                surface.blit(txt, (40, 120 + idx * 35))

            self.back_button.draw(surface, mouse_pos)

        elif self.state == "CREDITS":
            title = self.font_title.render("CRÉDITOS", True, COLOR_ACCENT)
            surface.blit(title, (40, 40))

            credits_lines = [
                "Recreación de Metal Gear 2: Solid Snake ( MSX2, 1990 )",
                "Herramientas: Python, Pygame-ce, Tiled, Pytmx",
                "Inspirado en la obra maestra de Hideo Kojima & Konami",
                "Desarrollado por Valentina Artaza, Ámbar Fiszman,",
                "Augusto Karacsany y Lautaro Medina. - ACT4AP [26-2]"
            ]
            for idx, line in enumerate(credits_lines):
                txt = self.font_btn.render(line, True, COLOR_TEXT)
                surface.blit(txt, (40, 120 + idx * 35))

            self.back_button.draw(surface, mouse_pos)