import random
import pygame

GRID_SIZE = 8
TILE_SIZE = 60
GEM_COLORS = [
    (220, 50, 50),   # Red
    (50, 200, 50),   # Green
    (50, 100, 240),  # Blue
    (240, 200, 40),  # Yellow
    (180, 50, 220),  # Purple
    (240, 130, 40),  # Orange
]


class Gem:
   
    def __init__(self, color, target_row, col):
        self.color = color
        self.target_row = target_row
        self.col = col
        
        self.is_bomb = False
        self.bomb_direction = None

        # Start higher up to animate falling down
        self.current_y = (target_row - 2) * TILE_SIZE
        self.target_y = target_row * TILE_SIZE
        self.fall_speed = 12.0

    def update(self):
        if self.current_y < self.target_y:
            self.current_y += self.fall_speed
            if self.current_y > self.target_y:
                self.current_y = self.target_y

    def is_animating(self):
        return self.current_y < self.target_y


class Board:
    """Manages animated gem grid, gravity drops, score, and game limits."""

    def __init__(self, offset_x, offset_y, target_score=500, max_moves=20):
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.target_score = target_score
        self.max_moves = max_moves
        self.grid = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.selected = None
        self.score = 0
        self.moves_remaining = max_moves

        self.idle_start_time = pygame.time.get_ticks()
        self.hint_positions = None
        self.hint_check_time = 0

        self.reset()

    def reset(self):
        """Reset board grid, score, and move limits."""
        self.score = 0
        self.moves_remaining = self.max_moves
        self.selected = None

        self.idle_start_time = pygame.time.get_ticks()
        self.hint_positions = None
        self.hint_check_time = 0

        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                color = random.choice(GEM_COLORS)
                gem = Gem(color, r, c)
                gem.current_y = gem.target_y  # Snap instantly on initial start
                self.grid[r][c] = gem

        self.resolve_matches()

    def is_animating(self):
        """Returns True if any gem is currently dropping down."""
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid[r][c] and self.grid[r][c].is_animating():
                    return True
        return False

    def swap_gems(self, pos1, pos2):
        """Swap positions and target render coordinates of two gems."""
        r1, c1 = pos1
        r2, c2 = pos2

        g1, g2 = self.grid[r1][c1], self.grid[r2][c2]
        self.grid[r1][c1], self.grid[r2][c2] = g2, g1

        if self.grid[r1][c1]:
            self.grid[r1][c1].target_row = r1
            self.grid[r1][c1].target_y = r1 * TILE_SIZE
            self.grid[r1][c1].current_y = r1 * TILE_SIZE

        if self.grid[r2][c2]:
            self.grid[r2][c2].target_row = r2
            self.grid[r2][c2].target_y = r2 * TILE_SIZE
            self.grid[r2][c2].current_y = r2 * TILE_SIZE

    def is_adjacent(self, pos1, pos2):
        r1, c1 = pos1
        r2, c2 = pos2
        return abs(r1 - r2) + abs(c1 - c2) == 1

    def find_matches(self):
        """Scan grid for horizontal and vertical 3-in-a-row color matches."""
        matched = set()

        # Horizontal matches
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE - 2):
                if (
                    self.grid[r][c]
                    and self.grid[r][c + 1]
                    and self.grid[r][c + 2]
                    and self.grid[r][c].color == self.grid[r][c + 1].color == self.grid[r][c + 2].color
                ):
                    matched.update([(r, c), (r, c + 1), (r, c + 2)])

        # Vertical matches
        for r in range(GRID_SIZE - 2):
            for c in range(GRID_SIZE):
                if (
                    self.grid[r][c]
                    and self.grid[r + 1][c]
                    and self.grid[r + 2][c]
                    and self.grid[r][c].color == self.grid[r + 1][c].color == self.grid[r + 2][c].color
                ):
                    matched.update([(r, c), (r + 1, c), (r + 2, c)])

        return matched

    def drop_and_refill(self):
        for c in range(GRID_SIZE):
            empty_slots = 0
            for r in range(GRID_SIZE - 1, -1, -1):
                if self.grid[r][c] is None:
                    empty_slots += 1
                elif empty_slots > 0:
                    gem = self.grid[r][c]
                    gem.target_row = r + empty_slots
                    gem.target_y = (r + empty_slots) * TILE_SIZE
                    self.grid[r + empty_slots][c] = gem
                    self.grid[r][c] = None

            for r in range(empty_slots):
                color = random.choice(GEM_COLORS)
                gem = Gem(color, r, c)
                gem.current_y = -((empty_slots - r) * TILE_SIZE)
                self.grid[r][c] = gem

    def resolve_matches(self, score_cascades=False):
        total_cleared = 0
        cascade_multiplier = 1

        while True:
            matches = self.find_matches()

            if not matches:
                break

            total_cleared += len(matches)

            if score_cascades:
                self.score += len(matches) * 10 * cascade_multiplier

            # Find exactly-4 matches and create bombs.
            bomb_matches = []

            # Horizontal
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE - 3):
                    if (
                        self.grid[r][c]
                        and self.grid[r][c + 1]
                        and self.grid[r][c + 2]
                        and self.grid[r][c + 3]
                        and self.grid[r][c].color
                        == self.grid[r][c + 1].color
                        == self.grid[r][c + 2].color
                        == self.grid[r][c + 3].color
                    ):
                        bomb_matches.append(((r, c + 1), "row"))

            # Vertical
            for r in range(GRID_SIZE - 3):
                for c in range(GRID_SIZE):
                    if (
                        self.grid[r][c]
                        and self.grid[r + 1][c]
                        and self.grid[r + 2][c]
                        and self.grid[r + 3][c]
                        and self.grid[r][c].color
                        == self.grid[r + 1][c].color
                        == self.grid[r + 2][c].color
                        == self.grid[r + 3][c].color
                    ):
                        bomb_matches.append(((r + 1, c), "column"))

            # Create Bomb Gems before clearing the match.
            for (r, c), direction in bomb_matches:
                if self.grid[r][c] is not None:
                    self.grid[r][c].is_bomb = True
                    self.grid[r][c].bomb_direction = direction

            # Find bombs that are part of this match.
            activated_bombs = []

            for r, c in matches:
                gem = self.grid[r][c]

                if gem is not None and gem.is_bomb:
                    activated_bombs.append((r, c, gem.bomb_direction))

            # Clear normal matched gems.
            for r, c in matches:
                self.grid[r][c] = None

            # Clear rows/columns from activated bombs.
            for r, c, direction in activated_bombs:
                if direction == "row":
                    for col in range(GRID_SIZE):
                        self.grid[r][col] = None

                elif direction == "column":
                    for row in range(GRID_SIZE):
                        self.grid[row][c] = None

            self.drop_and_refill()
            cascade_multiplier += 1

        return total_cleared

    def find_hint_swap(self):
        """Find an adjacent swap that creates a match."""
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                # Try swapping right
                if c < GRID_SIZE - 1:
                    pos1 = (r, c)
                    pos2 = (r, c + 1)

                    self.swap_gems(pos1, pos2)
                    matches = self.find_matches()
                    self.swap_gems(pos1, pos2)

                    if matches:
                        return pos1, pos2

                # Try swapping down
                if r < GRID_SIZE - 1:
                    pos1 = (r, c)
                    pos2 = (r + 1, c)

                    self.swap_gems(pos1, pos2)
                    matches = self.find_matches()
                    self.swap_gems(pos1, pos2)

                    if matches:
                        return pos1, pos2

        return None

    def process_swap(self, pos1, pos2):
        if not self.is_adjacent(pos1, pos2) or self.is_game_over() or self.is_animating():
            return False

        self.swap_gems(pos1, pos2)
        matches = self.find_matches()

        # BUG SYMPTOM:
        # Move count decrements on EVERY swap attempt even invalid ones.
        

        if not matches:
            self.swap_gems(pos1, pos2)  # Revert invalid swap
            return False
        self.moves_remaining -= 1

        self.idle_start_time = pygame.time.get_ticks()
        self.hint_positions = None
        self.hint_check_time = 0

        #cleared = self.resolve_matches()
        #self.score += cleared * 10
        self.resolve_matches(score_cascades=True)
        return True

    def is_game_over(self):
        return self.score >= self.target_score or self.moves_remaining <= 0

    def check_result(self):
        if self.score >= self.target_score:
            return "WIN"
        if self.moves_remaining <= 0:
            return "LOSS"
        return None

    def update(self):
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid[r][c]:
                    self.grid[r][c].update()

        # Do not show hints while gems are falling.
        if self.is_animating():
            self.hint_positions = None
            self.idle_start_time = pygame.time.get_ticks()
            return

        current_time = pygame.time.get_ticks()

        # Player has been idle for more than 5 seconds.
        if current_time - self.idle_start_time >= 5000:
            if self.hint_positions is None:
                # Avoid repeatedly searching the board every frame.
                if current_time - self.hint_check_time >= 1000:
                    self.hint_check_time = current_time
                    self.hint_positions = self.find_hint_swap()

    def render(self, surface):
        board_rect = pygame.Rect(
            self.offset_x, self.offset_y, GRID_SIZE * TILE_SIZE, GRID_SIZE * TILE_SIZE
        )
        pygame.draw.rect(surface, (20, 22, 28), board_rect, border_radius=8)
        pygame.draw.rect(surface, (60, 65, 75), board_rect, width=3, border_radius=8)

        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                gem = self.grid[r][c]
                if gem:
                    x = self.offset_x + c * TILE_SIZE
                    y = self.offset_y + gem.current_y
                    tile_rect = pygame.Rect(x + 2, y + 2, TILE_SIZE - 4, TILE_SIZE - 4)

                    pygame.draw.rect(surface, gem.color, tile_rect, border_radius=10)
                    pygame.draw.rect(
                        surface, (255, 255, 255), tile_rect, width=1, border_radius=10
                    )

                    if self.hint_positions and (r, c) in self.hint_positions:
                        pulse = (pygame.time.get_ticks() // 150) % 2

                        if pulse:
                            pygame.draw.rect(
                                surface,
                                (255, 255, 255),
                                tile_rect.inflate(8, 8),
                                width=4,
                                border_radius=12,
                            )

                if self.selected == (r, c):
                    sel_x = self.offset_x + c * TILE_SIZE
                    sel_y = self.offset_y + r * TILE_SIZE
                    sel_rect = pygame.Rect(sel_x + 2, sel_y + 2, TILE_SIZE - 4, TILE_SIZE - 4)
                    pygame.draw.rect(
                        surface, (255, 255, 255), sel_rect, width=4, border_radius=10
                    )