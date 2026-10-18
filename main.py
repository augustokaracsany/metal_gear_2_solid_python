import pygame
import sys
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
from src.menu import MenuManager
from src.intro_state import IntroState
from src.game import Game  # Clase principal de juego ( El game.py. )


def main():
    pygame.init()
    pygame.mixer.init()
    
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Metal Gear 2: Solid Python")
    clock = pygame.time.Clock()

    # 1. Cargar automáticamente los 60 frames de la intro 1.
    intro_frames_1 = []
    for i in range(1, 61):
        path = f"assets/intro/frame{i}.png"
        try:
            img = pygame.image.load(path).convert_alpha()
            intro_frames_1.append(img)
        except Exception as e:
            print(f"Aviso: No se pudo cargar el archivo {path}: {e}")

    # 2. Cargar automáticamente los 70 frames de la secuencia 2.
    intro_frames_2 = []
    for i in range(1, 71):
        path = f"assets/intro/sec2/frame{i}.png"
        try:
            img = pygame.image.load(path).convert_alpha()
            intro_frames_2.append(img)
        except Exception as e:
            print(f"Aviso: No se pudo cargar el archivo {path}: {e}")

    # Definir el guion de secuencias modular:
    # - Secuencia 1: Del 1 al 60, con el tramo del 8 al 60 repetido 3 veces.
    # - Secuencia 2: De corrido desde el frame 1 al 70 (sin bucles adicionales).
    intro_script = [
        {
            "frames": intro_frames_1,
            "scale": 2,
            "fps": 0.15,
            "play_once": range(0, min(60, len(intro_frames_1))),
            "loop_range": range(7, min(60, len(intro_frames_1))),
            "loop_count": 3,
        },
        {
            "frames": intro_frames_2,
            "scale": 2,
            "fps": 0.15,
            "play_once": range(0, len(intro_frames_2)), # Reproducción lineal de corrido
        }
    ]

    # Ruta de la música global para la intro
    music_file = r"assets\audio\music\Theme_of_Solid_Snake.mp3"

    # Estados iniciales.
    current_state = IntroState(intro_script, music_path=music_file)
    menu_manager = MenuManager()
    game_instance = None

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # Delta Time en segundos.
        events = pygame.event.get()

        # 1. GESTIÓN DE EVENTOS SEGÚN ESTADO ACTUAL.
        if isinstance(current_state, IntroState):
            current_state.handle_events(events)
            current_state.update(dt)
            if current_state.finished:
                # Al terminar la intro completa, pasa al Menú Principal.
                current_state = menu_manager

        elif current_state == menu_manager:
            action = menu_manager.handle_events(events)
            if action == "EXIT":
                running = False
            elif action == "REPLAY_INTRO":
                current_state = IntroState(intro_script, music_path=music_file)
            elif action and action.startswith("START_MISSION_"):
                mission_num = int(action.split("_")[-1])
                # Iniciar el juego con la misión seleccionada.
                game_instance = Game(mission_num)
                current_state = game_instance

        elif isinstance(current_state, Game):
            # Se delegan los eventos al juego. Como la ACCIÓN DE GOLPEAR. ( E. )
            current_state.handle_events(events)

            if getattr(current_state, "return_to_menu", False):
                current_state = menu_manager
                
            # Si el jugador presiona ESC dentro del juego, se vuelve al menú principal:
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    current_state = menu_manager  # Volver al menú

            # Una única llamada limpia al update por frame
            if isinstance(current_state, Game): # Nos aseguramos de seguir en el juego por si presionó ESC
                current_state.update(dt)

        # 2. RENDERIZADO.
        screen.fill((0, 0, 0))
        current_state.draw(screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()