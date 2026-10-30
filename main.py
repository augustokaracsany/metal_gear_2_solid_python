import pygame
import sys
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
from src.menu import MenuManager
from src.prologue import PrologueState
from src.intro_state import IntroState
from src.game import Game 
from src.main_menu_view import MainMenuView
from src.cinematic_intro import CinematicIntroState
from src.game import Game  # Clase principal de juego ( El game.py. )
from src.codec import CodecManager


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
            "play_once": range(0, len(intro_frames_2)),
        }
    ]

    # Ruta de la música global para la intro
    music_file = r"assets\audio\music\Theme_of_Solid_Snake.mp3"

    # Estados iniciales.s
    current_state = IntroState(intro_script, music_path=music_file)
    menu_manager = MenuManager()
    game_instance = None

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # Delta Time en segundos.
        events = pygame.event.get()

        # 1. GESTIÓN DE EVENTOS Y ACTUALIZACIÓN SEGÚN ESTADO ACTUAL.
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
                if mission_num == 1:
                    # Asignamos el prólogo como estado inicial al elegir la misión 1
                    prologue_instance = PrologueState()
                    prologue_instance.target_mission = mission_num 
                    current_state = prologue_instance
                else:
                    # Si es otra misión sin prólogo, entra directo
                    current_state = Game(mission_num)

        elif isinstance(current_state, Game):
            # Procesa los eventos dentro de Game (pausa, jugador, teclado)
            game_action = current_state.handle_events(events)
            
            # Si en el menú de pausa se selecciona "VOLVER AL MENÚ"
            if game_action == "GOTO_MENU":
                menu_manager.state = "MAIN_MENU"   # <- agregar
                game_instance = None               # <- opcional, libera la partida
                current_state = menu_manager

            if getattr(current_state, "return_to_menu", False):
                current_state = menu_manager
                
            for event in events:
                if event.type == pygame.QUIT:
                    running = False

            if isinstance(current_state, Game): 
                current_state.update(dt, screen)

        elif isinstance(current_state, PrologueState):
            current_state.handle_events(events)
            current_state.update(dt)
            if current_state.finished:
                # AL TERMINAR EL PRÓLOGO: Pasamos a la cinemática de escalada
                current_state = CinematicIntroState()

        elif isinstance(current_state, CinematicIntroState):
            # AL ESTAR EN LA CINEMÁTICA DE ESCALADA:
            current_state.handle_events(events)
            current_state.update(dt)
            if getattr(current_state, "finished", False):
                codec_state = CodecManager()
                codec_state.start_call("intro_first_mission")
                current_state = codec_state

        elif isinstance(current_state, CodecManager):
            current_state.handle_input(events)
            current_state.update(dt)
            
            if getattr(current_state, "finished", False):
                current_state = Game(1)

        # 2. RENDERIZADO GLOBAL.
        screen.fill((0, 0, 0))
        current_state.draw(screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()