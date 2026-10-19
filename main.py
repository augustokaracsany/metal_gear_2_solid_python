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
    music_file = r"C:\Users\Agues\Documents\GitHub\metal_gear_2_solid_python\assets\audio\music\Theme_of_Solid_Snake.mp3"

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
            # Procesa los eventos dentro de Game (pausa, jugador, teclado)
            game_action = current_state.handle_events(events)
            
            # Si en el menú de pausa se selecciona "VOLVER AL MENÚ"
            if game_action == "GOTO_MENU":
                menu_manager.state = "MAIN_MENU"   # <- agregar
                game_instance = None               # <- opcional, libera la partida
                current_state = menu_manager

            current_state.update(dt) # CLAVE. NO CAMBIAR.

        # 2. RENDERIZADO.m
        screen.fill((0, 0, 0))
        current_state.draw(screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
