"""HTML5 테트리스를 pygame으로 포팅한 단일 파일 게임."""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from typing import Optional

import pygame


COLUMNS = 10
ROWS = 20
CELL_SIZE = 30
BOARD_WIDTH = COLUMNS * CELL_SIZE
BOARD_HEIGHT = ROWS * CELL_SIZE
SIDEBAR_WIDTH = 260
WINDOW_WIDTH = BOARD_WIDTH + SIDEBAR_WIDTH + 72
WINDOW_HEIGHT = BOARD_HEIGHT + 100
FPS = 60

BG = (11, 13, 24)
BOARD_BG = (9, 11, 21)
PANEL_BG = (20, 24, 45)
GRID = (26, 31, 55)
LINE = (53, 60, 96)
TEXT = (245, 247, 255)
MUTED = (139, 145, 169)
CYAN = (87, 243, 220)
PINK = (255, 78, 151)
YELLOW = (255, 216, 90)
COLORS = [None, CYAN, (92, 124, 255), (255, 159, 67), YELLOW, (157, 114, 255), (99, 230, 109), PINK]

PIECES = (
    ((1, 1, 1, 1),),
    ((2, 0, 0), (2, 2, 2)),
    ((0, 0, 3), (3, 3, 3)),
    ((4, 4), (4, 4)),
    ((0, 5, 0), (5, 5, 5)),
    ((0, 6, 6), (6, 6, 0)),
    ((7, 7, 0), (0, 7, 7)),
)


@dataclass
class Piece:
    shape: list[list[int]]
    x: int
    y: int


def create_board() -> list[list[int]]:
    return [[0 for _ in range(COLUMNS)] for _ in range(ROWS)]


def random_piece() -> Piece:
    source = random.choice(PIECES)
    shape = [list(row) for row in source]
    return Piece(shape, (COLUMNS - len(shape[0])) // 2, 0)


def rotate(shape: list[list[int]]) -> list[list[int]]:
    return [list(row) for row in zip(*shape[::-1])]


def collides(board: list[list[int]], piece: Piece, move_x: int = 0,
             move_y: int = 0, shape: Optional[list[list[int]]] = None) -> bool:
    shape = shape or piece.shape
    for y, row in enumerate(shape):
        for x, value in enumerate(row):
            if not value:
                continue
            board_x = piece.x + x + move_x
            board_y = piece.y + y + move_y
            if board_x < 0 or board_x >= COLUMNS or board_y >= ROWS:
                return True
            if board_y >= 0 and board[board_y][board_x]:
                return True
    return False


def draw_block(surface: pygame.Surface, x: int, y: int, color_index: int,
               size: int = CELL_SIZE, alpha: int = 255) -> None:
    color = COLORS[color_index]
    block = pygame.Surface((size - 2, size - 2), pygame.SRCALPHA)
    block.fill((*color, alpha))
    pygame.draw.rect(block, (*TEXT, min(alpha, 100)), (1, 1, size - 4, 3))
    pygame.draw.rect(block, (0, 0, 0, min(alpha, 70)), (1, size - 6, size - 4, 3))
    surface.blit(block, (x * size + 1, y * size + 1))


class TetrisGame:
    def __init__(self) -> None:
        self.board = create_board()
        self.active_piece: Optional[Piece] = None
        self.next_piece = random_piece()
        self.score = 0
        self.lines = 0
        self.level = 1
        self.state = "ready"
        self.drop_timer = 0

    def reset(self) -> None:
        self.board = create_board()
        self.active_piece = random_piece()
        self.next_piece = random_piece()
        self.score = 0
        self.lines = 0
        self.level = 1
        self.state = "playing"
        self.drop_timer = 0

    def move(self, direction: int) -> None:
        if self.state == "playing" and self.active_piece and not collides(self.board, self.active_piece, direction):
            self.active_piece.x += direction

    def rotate_piece(self) -> None:
        if self.state != "playing" or not self.active_piece:
            return
        rotated = rotate(self.active_piece.shape)
        for offset in (0, -1, 1, -2, 2):
            if not collides(self.board, self.active_piece, offset, shape=rotated):
                self.active_piece.x += offset
                self.active_piece.shape = rotated
                return

    def drop(self) -> None:
        if self.state != "playing" or not self.active_piece:
            return
        if not collides(self.board, self.active_piece, move_y=1):
            self.active_piece.y += 1
            self.drop_timer = 0
        else:
            self.lock_piece()

    def hard_drop(self) -> None:
        if self.state != "playing" or not self.active_piece:
            return
        distance = 0
        while not collides(self.board, self.active_piece, move_y=1):
            self.active_piece.y += 1
            distance += 1
        self.score += distance * 2
        self.lock_piece()

    def lock_piece(self) -> None:
        if not self.active_piece:
            return
        for y, row in enumerate(self.active_piece.shape):
            for x, value in enumerate(row):
                board_y = self.active_piece.y + y
                board_x = self.active_piece.x + x
                if value and board_y >= 0:
                    self.board[board_y][board_x] = value
        self.clear_lines()
        self.active_piece = self.next_piece
        self.next_piece = random_piece()
        if collides(self.board, self.active_piece):
            self.state = "over"

    def clear_lines(self) -> None:
        completed = sum(all(row) for row in self.board)
        if not completed:
            return
        self.board = [row for row in self.board if not all(row)]
        self.board = [[0] * COLUMNS for _ in range(completed)] + self.board
        self.score += (0, 100, 300, 500, 800)[completed] * self.level
        self.lines += completed
        self.level = self.lines // 10 + 1

    def update(self, milliseconds: int) -> None:
        if self.state != "playing":
            return
        self.drop_timer += milliseconds
        interval = max(90, 800 - (self.level - 1) * 65)
        if self.drop_timer > interval:
            self.drop()

    def toggle_pause(self) -> None:
        if self.state == "playing":
            self.state = "paused"
        elif self.state == "paused":
            self.state = "playing"


def draw_text(surface: pygame.Surface, font: pygame.font.Font, text: str,
              position: tuple[int, int], color: tuple[int, int, int] = TEXT,
              center: bool = False) -> None:
    image = font.render(text, True, color)
    rect = image.get_rect()
    if center:
        rect.center = position
    else:
        rect.topleft = position
    surface.blit(image, rect)


def draw_piece(surface: pygame.Surface, piece: Piece, alpha: int = 255) -> None:
    for y, row in enumerate(piece.shape):
        for x, value in enumerate(row):
            if value:
                draw_block(surface, piece.x + x, piece.y + y, value, alpha=alpha)


def draw_board(surface: pygame.Surface, game: TetrisGame) -> None:
    pygame.draw.rect(surface, BOARD_BG, (0, 0, BOARD_WIDTH, BOARD_HEIGHT))
    for x in range(COLUMNS + 1):
        pygame.draw.line(surface, GRID, (x * CELL_SIZE, 0), (x * CELL_SIZE, BOARD_HEIGHT))
    for y in range(ROWS + 1):
        pygame.draw.line(surface, GRID, (0, y * CELL_SIZE), (BOARD_WIDTH, y * CELL_SIZE))
    for y, row in enumerate(game.board):
        for x, value in enumerate(row):
            if value:
                draw_block(surface, x, y, value)
    if game.active_piece:
        ghost = Piece(game.active_piece.shape, game.active_piece.x, game.active_piece.y)
        while not collides(game.board, ghost, move_y=1):
            ghost.y += 1
        draw_piece(surface, ghost, alpha=45)
        draw_piece(surface, game.active_piece)


def draw_next(surface: pygame.Surface, game: TetrisGame) -> None:
    preview = pygame.Surface((128, 128))
    preview.fill((11, 14, 27))
    shape = game.next_piece.shape
    offset_x = (4 - len(shape[0])) / 2
    offset_y = (4 - len(shape)) / 2
    for y, row in enumerate(shape):
        for x, value in enumerate(row):
            if value:
                draw_block(preview, int(offset_x + x), int(offset_y + y), value, size=32)
    surface.blit(preview, (BOARD_WIDTH + 52, 170))


def draw_ui(screen: pygame.Surface, game: TetrisGame, fonts: dict[str, pygame.font.Font]) -> None:
    title_font = fonts["title"]
    small_font = fonts["small"]
    mono_font = fonts["mono"]
    x = BOARD_WIDTH + 36
    pygame.draw.line(screen, LINE, (24, 64), (WINDOW_WIDTH - 24, 64))
    draw_text(screen, title_font, "NEON TETRIS", (24, 24), CYAN)
    status = {"ready": "READY TO PLAY", "playing": "RUNNING", "paused": "PAUSED", "over": "GAME OVER"}[game.state]
    draw_text(screen, small_font, status, (WINDOW_WIDTH - 142, 32), MUTED)

    pygame.draw.rect(screen, PANEL_BG, (x, 86, SIDEBAR_WIDTH, 184))
    pygame.draw.line(screen, PINK, (x, 86), (x + SIDEBAR_WIDTH, 86), 2)
    draw_text(screen, small_font, "SCORE", (x + 20, 104), CYAN)
    draw_text(screen, mono_font, f"{game.score:06d}", (x + 20, 128), YELLOW)
    draw_text(screen, small_font, "LINES", (x + 20, 188), MUTED)
    draw_text(screen, mono_font, f"{game.lines:03d}", (x + 170, 188))
    draw_text(screen, small_font, "LEVEL", (x + 20, 228), MUTED)
    draw_text(screen, mono_font, f"{game.level:02d}", (x + 170, 228))

    pygame.draw.rect(screen, PANEL_BG, (x, 286, SIDEBAR_WIDTH, 184))
    draw_text(screen, small_font, "NEXT BLOCK", (x + 20, 304), CYAN)
    draw_next(screen, game)

    pygame.draw.rect(screen, PANEL_BG, (x, 486, SIDEBAR_WIDTH, 142))
    draw_text(screen, small_font, "CONTROLS", (x + 20, 504), CYAN)
    controls = [("LEFT / RIGHT", "MOVE"), ("DOWN", "SOFT DROP"), ("UP", "ROTATE"), ("SPACE", "HARD DROP"), ("P", "PAUSE")]
    for index, (key, action) in enumerate(controls):
        draw_text(screen, mono_font, key, (x + 20, 528 + index * 19), TEXT)
        draw_text(screen, small_font, action, (x + 145, 528 + index * 19), MUTED)


def draw_overlay(screen: pygame.Surface, game: TetrisGame, fonts: dict[str, pygame.font.Font]) -> None:
    if game.state == "playing":
        return
    veil = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    veil.fill((9, 11, 21, 220))
    screen.blit(veil, (0, 0))
    title = {"ready": "테트리스", "paused": "일시정지", "over": "게임 종료"}[game.state]
    message = {"ready": "블록을 쌓아 줄을 완성하세요.", "paused": "P를 눌러 계속하기", "over": f"최종 점수: {game.score:06d}"}[game.state]
    draw_text(screen, fonts["small"], "SYSTEM READY" if game.state == "ready" else "RUN COMPLETE", (BOARD_WIDTH // 2, 250), CYAN, center=True)
    draw_text(screen, fonts["title"], title, (BOARD_WIDTH // 2, 295), TEXT, center=True)
    draw_text(screen, fonts["small"], message, (BOARD_WIDTH // 2, 340), MUTED, center=True)
    if game.state == "ready" or game.state == "over":
        draw_text(screen, fonts["button"], "ENTER: START / RESTART", (BOARD_WIDTH // 2, 390), PINK, center=True)


def main() -> None:
    pygame.init()
    pygame.display.set_caption("NEON TETRIS - Python Edition")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    fonts = {
        "title": pygame.font.SysFont("consolas", 25, bold=True),
        "small": pygame.font.SysFont("consolas", 13),
        "mono": pygame.font.SysFont("consolas", 16),
        "button": pygame.font.SysFont("consolas", 14, bold=True),
    }
    game = TetrisGame()
    running = True

    while running:
        elapsed = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and game.state in ("ready", "over"):
                    game.reset()
                elif event.key == pygame.K_LEFT:
                    game.move(-1)
                elif event.key == pygame.K_RIGHT:
                    game.move(1)
                elif event.key == pygame.K_DOWN:
                    game.drop()
                elif event.key == pygame.K_UP:
                    game.rotate_piece()
                elif event.key == pygame.K_SPACE:
                    game.hard_drop()
                elif event.key == pygame.K_p:
                    game.toggle_pause()
        game.update(elapsed)
        screen.fill(BG)
        draw_board(screen, game)
        draw_ui(screen, game, fonts)
        draw_overlay(screen, game, fonts)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
