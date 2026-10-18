import pygame

class Item(pygame.sprite.Sprite):
    def __init__(self, name, x, y, image_path, scale=1):
        super().__init__()
        self.name = name  # "cardboard_box"
        self.image = pygame.image.load(image_path).convert_alpha()
        if scale != 1:
            self.image = pygame.transform.scale(
                self.image,
                (int(self.image.get_width() * scale), int(self.image.get_height() * scale))
            )
        self.rect = self.image.get_rect(topleft=(x, y))