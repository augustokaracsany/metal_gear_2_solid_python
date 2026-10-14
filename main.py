import pygame
import sys
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
from src.menu import MenuManager
from src.intro import IntroState
from src.game import Game  # Clase principal de juego ( El game.py. )

def main():
    pygame.init()
    pygame.mixer.init()
    
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Metal Gear 2: Solid Python")
    clock = pygame.time.Clock()

    # Cargar automáticamente los 12 frames de la intro.
    intro_frames = []
    for i in range(1, 13):
        path = f"assets/intro/frame{i}.png"
        try:
            img = pygame.image.load(path).convert_alpha()
            # Escalar los frames = resolución pantalla:
            # img = pygame.transform.scale(img, (ANCHO_DESEADO, ALTO_DESEADO))
            intro_frames.append(img)
        except Exception as e:
            print(f"Aviso: No se pudo cargar el archivo {path}: {e}")

    # Iniciar el estado de la intro con los frames reales.
    current_state = IntroState(intro_frames, max_loops=30)

    # Estados iniciales.
    current_state = IntroState(intro_frames)
    menu_manager = MenuManager()
    game_instance = None

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # Delta Time en segundos. dt
        events = pygame.event.get()

        # 1. GESTIÓN DE EVENTOS SEGÚN ESTADO ACTUAL.
        if isinstance(current_state, IntroState):
            current_state.handle_events(events)
            current_state.update(dt)
            if current_state.finished:
                # Al terminar la intro, pasa al Menú Principal.
                current_state = menu_manager

        elif current_state == menu_manager:
            action = menu_manager.handle_events(events)
            if action == "EXIT":
                running = False
            elif action == "REPLAY_INTRO":
                current_state = IntroState(intro_frames)
            elif action and action.startswith("START_MISSION_"):
                mission_num = int(action.split("_")[-1])
                # Iniciar el juego con la misión seleccionada. Número de misión.
                game_instance = Game(mission_num)
                current_state = game_instance

        elif isinstance(current_state, Game):
            # Se delegan los eventos al juego. Como la ACCIÓN DE GOLPEAR. ( E. )
            current_state.handle_events(events)
            # Si el jugador presiona ESC dentro del juego, se vuelve al menú principal:
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    current_state = menu_manager  # Volver al menú

            current_state.update(dt) # CLAVE. NO CAMBIAR.

        # 2. RENDERIZADO.
        screen.fill((0, 0, 0))
        current_state.draw(screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()