"""pygame으로 만든 간단한 뱀게임."""

from __future__ import annotations

import random
import sys
from collections.abc import Iterable

import pygame


CELL_SIZE = 24
COLUMNS = 24
ROWS = 24
BOARD_WIDTH = COLUMNS * CELL_SIZE
BOARD_HEIGHT = ROWS * CELL_SIZE
SIDEBAR_WIDTH = 220
WINDOW_WIDTH = BOARD_WIDTH + SIDEBAR_WIDTH
WINDOW_HEIGHT = BOARD_HEIGHT
FPS = 60
MOVE_INTERVAL = 115

BACKGROUND = (8, 15, 18)
BOARD_BACKGROUND = (11, 23, 25)
PANEL_BACKGROUND = (18, 35, 36)
GRID = (22, 47, 47)
TEXT = (240, 247, 231)
MUTED = (137, 164, 151)
GREEN = (177, 231, 91)
BRIGHT_GREEN = (218, 255, 116)
RED = (255, 103, 91)
ORANGE = (255, 173, 81)

Point = tuple[int, int]


def draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    position: tuple[int, int],
    color: tuple[int, int, int] = TEXT,
    center: bool = False,
) -> None:
    image = font.render(text, True, color)
    rectangle = image.get_rect()
    if center:
        rectangle.center = position
    else:
        rectangle.topleft = position
    surface.blit(image, rectangle)


def random_food(snake: Iterable[Point]) -> Point:
    occupied = set(snake)
    available = [
        (x, y)
        for y in range(ROWS)
        for x in range(COLUMNS)
        if (x, y) not in occupied
    ]
    return random.choice(available)


class SnakeGame:
    def __init__(self) -> None:
        self.best_score = 0
        self.reset()

    def reset(self) -> None:
        center = (COLUMNS // 2, ROWS // 2)
        self.snake: list[Point] = [center, (center[0] - 1, center[1]), (center[0] - 2, center[1])]
        self.direction: Point = (1, 0)
        self.next_direction: Point = self.direction
        self.food = random_food(self.snake)
        self.score = 0
        self.state = "ready"
        self.move_timer = 0

    def start(self) -> None:
        if self.state in {"ready", "over"}:
            self.reset()
        self.state = "playing"

    def toggle_pause(self) -> None:
        if self.state == "playing":
            self.state = "paused"
        elif self.state == "paused":
            self.state = "playing"

    def set_direction(self, direction: Point) -> None:
        if direction != (-self.direction[0], -self.direction[1]):
            self.next_direction = direction

    def update(self, milliseconds: int) -> None:
        if self.state != "playing":
            return
        self.move_timer += milliseconds
        if self.move_timer < MOVE_INTERVAL:
            return
        self.move_timer = 0
        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        new_head = (head_x + self.direction[0], head_y + self.direction[1])
        hit_wall = not (0 <= new_head[0] < COLUMNS and 0 <= new_head[1] < ROWS)
        hit_body = new_head in self.snake[:-1]
        if hit_wall or hit_body:
            self.state = "over"
            self.best_score = max(self.best_score, self.score)
            return
        self.snake.insert(0, new_head)
        if new_head == self.food:
            self.score += 10
            self.best_score = max(self.best_score, self.score)
            self.food = random_food(self.snake)
        else:
            self.snake.pop()


def draw_board(screen: pygame.Surface, game: SnakeGame) -> None:
    board_rectangle = pygame.Rect(0, 0, BOARD_WIDTH, BOARD_HEIGHT)
    pygame.draw.rect(screen, BOARD_BACKGROUND, board_rectangle)
    for x in range(COLUMNS + 1):
        pygame.draw.line(screen, GRID, (x * CELL_SIZE, 0), (x * CELL_SIZE, BOARD_HEIGHT))
    for y in range(ROWS + 1):
        pygame.draw.line(screen, GRID, (0, y * CELL_SIZE), (BOARD_WIDTH, y * CELL_SIZE))

    food_x, food_y = game.food
    food_center = (food_x * CELL_SIZE + CELL_SIZE // 2, food_y * CELL_SIZE + CELL_SIZE // 2)
    pygame.draw.circle(screen, RED, food_center, CELL_SIZE // 3)
    pygame.draw.circle(screen, ORANGE, (food_center[0] + 4, food_center[1] - 4), 3)

    for index, (x, y) in enumerate(game.snake):
        rectangle = pygame.Rect(x * CELL_SIZE + 2, y * CELL_SIZE + 2, CELL_SIZE - 4, CELL_SIZE - 4)
        color = BRIGHT_GREEN if index == 0 else GREEN
        pygame.draw.rect(screen, color, rectangle, border_radius=5)
        if index == 0:
            eye_color = (25, 45, 30)
            eye_x = rectangle.centerx + game.direction[0] * 4
            eye_y = rectangle.centery + game.direction[1] * 4
            pygame.draw.circle(screen, eye_color, (eye_x - 3, eye_y - 3), 2)
            pygame.draw.circle(screen, eye_color, (eye_x + 3, eye_y + 3), 2)


def draw_panel(screen: pygame.Surface, game: SnakeGame, fonts: dict[str, pygame.font.Font]) -> None:
    panel_x = BOARD_WIDTH + 24
    pygame.draw.rect(screen, PANEL_BACKGROUND, (panel_x, 24, SIDEBAR_WIDTH - 48, 210), border_radius=6)
    pygame.draw.line(screen, GREEN, (panel_x, 24), (panel_x + SIDEBAR_WIDTH - 48, 24), 3)
    draw_text(screen, fonts["small"], "SNAKE // ARCADE", (panel_x + 18, 44), GREEN)
    draw_text(screen, fonts["label"], "SCORE", (panel_x + 18, 84), MUTED)
    draw_text(screen, fonts["score"], f"{game.score:05d}", (panel_x + 18, 105), BRIGHT_GREEN)
    draw_text(screen, fonts["label"], "BEST", (panel_x + 18, 164), MUTED)
    draw_text(screen, fonts["mono"], f"{game.best_score:05d}", (panel_x + 112, 164))

    draw_text(screen, fonts["label"], "CONTROL", (panel_x + 18, 275), GREEN)
    controls = (("ARROWS / WASD", "MOVE"), ("P", "PAUSE"), ("ENTER", "START"))
    for index, (key, action) in enumerate(controls):
        y = 310 + index * 35
        draw_text(screen, fonts["mono"], key, (panel_x + 18, y), TEXT)
        draw_text(screen, fonts["small"], action, (panel_x + 18, y + 16), MUTED)


def draw_overlay(screen: pygame.Surface, game: SnakeGame, fonts: dict[str, pygame.font.Font]) -> None:
    if game.state == "playing":
        return
    overlay = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    overlay.fill((3, 10, 12, 190))
    screen.blit(overlay, (0, 0))
    messages = {
        "ready": ("SNAKE", "ENTER를 눌러 시작"),
        "paused": ("PAUSED", "P를 눌러 계속하기"),
        "over": ("GAME OVER", "ENTER를 눌러 다시 시작"),
    }
    title, subtitle = messages[game.state]
    draw_text(screen, fonts["title"], title, (BOARD_WIDTH // 2, BOARD_HEIGHT // 2 - 28), BRIGHT_GREEN, center=True)
    draw_text(screen, fonts["small"], subtitle, (BOARD_WIDTH // 2, BOARD_HEIGHT // 2 + 28), TEXT, center=True)


def handle_event(event: pygame.event.Event, game: SnakeGame) -> None:
    if event.type == pygame.QUIT:
        pygame.quit()
        sys.exit()
    if event.type != pygame.KEYDOWN:
        return
    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        game.start()
    elif event.key == pygame.K_p:
        game.toggle_pause()
    else:
        directions = {
            pygame.K_UP: (0, -1), pygame.K_w: (0, -1),
            pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1),
            pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0),
            pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
        }
        if event.key in directions:
            game.set_direction(directions[event.key])


def main() -> None:
    pygame.init()
    pygame.display.set_caption("MY SNAKE // pygame")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    fonts = {
        "title": pygame.font.Font(None, 54),
        "score": pygame.font.Font(None, 42),
        "label": pygame.font.Font(None, 20),
        "small": pygame.font.Font(None, 24),
        "mono": pygame.font.Font(None, 22),
    }
    game = SnakeGame()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                handle_event(event, game)
        game.update(clock.get_time())
        screen.fill(BACKGROUND)
        draw_board(screen, game)
        draw_panel(screen, game, fonts)
        draw_overlay(screen, game, fonts)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


if __name__ == "__main__":
    main()