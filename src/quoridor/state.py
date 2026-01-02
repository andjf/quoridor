from __future__ import annotations

import heapq
from collections.abc import Iterator
from typing import Self

from quoridor.constants import (
    BOARD_SIZE,
    INITIAL_WALL_COUNT,
    MAX_PATH_COST,
)
from quoridor.model_types import (
    Move,
    MoveType,
    Orientation,
    Player,
    Vector,
    Wall,
)


class QuoridorState:
    def __init__(
        self,
        light_pos: Vector | None = None,
        dark_pos: Vector | None = None,
        walls: set[Wall] | None = None,
        turn: Player = Player.LIGHT,
        light_walls: int = INITIAL_WALL_COUNT,
        dark_walls: int = INITIAL_WALL_COUNT,
    ) -> None:
        self.light_pos = light_pos or Vector(0, BOARD_SIZE // 2)
        self.dark_pos = dark_pos or Vector(BOARD_SIZE - 1, BOARD_SIZE // 2)
        self.walls = walls if walls is not None else set()
        self.turn = turn
        self.light_walls_left = light_walls
        self.dark_walls_left = dark_walls

    def get_player_pos(self, player: Player) -> Vector:
        return self.light_pos if player == Player.LIGHT else self.dark_pos

    def check_winner(self) -> Player | None:
        if self.light_pos[0] == Player.LIGHT.goal_row:
            return Player.LIGHT
        if self.dark_pos[0] == Player.DARK.goal_row:
            return Player.DARK
        return None

    def apply_move(self, move: Move) -> Self:
        move_type, data = move
        new_state = QuoridorState(
            self.light_pos,
            self.dark_pos,
            self.walls.copy(),
            self.turn.opponent,
            self.light_walls_left,
            self.dark_walls_left,
        )

        if move_type == MoveType.MOVE:
            target_pos: Vector = data
            if self.turn == Player.LIGHT:
                new_state.light_pos = target_pos
            else:
                new_state.dark_pos = target_pos

        elif move_type == MoveType.WALL:
            wall: Wall = data
            new_state.walls.add(wall)
            if self.turn == Player.LIGHT:
                new_state.light_walls_left -= 1
            else:
                new_state.dark_walls_left -= 1
        return new_state

    def can_move(self, start: Vector, end: Vector) -> bool:
        return self._in_bounds(end) and not self.is_blocked(start, end)

    def is_blocked(self, start: Vector, end: Vector) -> bool:
        sr, sc = start
        er, ec = end

        # Vertical Movement (Crossing Horizontal Walls)
        if abs(sr - er) == 1 and sc == ec:
            r_min = min(sr, er)
            if ((r_min, sc), Orientation.HORIZONTAL) in self.walls:
                return True
            if ((r_min, sc - 1), Orientation.HORIZONTAL) in self.walls:
                return True

        # Horizontal Movement (Crossing Vertical Walls)
        elif abs(sc - ec) == 1 and sr == er:
            c_min = min(sc, ec)
            if ((sr, c_min), Orientation.VERTICAL) in self.walls:
                return True
            if ((sr - 1, c_min), Orientation.VERTICAL) in self.walls:
                return True

        return False

    def shortest_path_len(self, player: Player) -> int:
        start_pos = self.get_player_pos(player)
        goal_row = player.goal_row
        queue: list[tuple[int, Vector]] = [(0, start_pos)]
        visited: set[Vector] = {start_pos}

        while queue:
            dist, vec = heapq.heappop(queue)
            r, c = vec
            if r == goal_row:
                return dist

            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                    target = Vector(nr, nc)
                    if target not in visited and not self.is_blocked((r, c), target):
                        visited.add(target)
                        heapq.heappush(queue, (dist + 1, target))
        return MAX_PATH_COST

    def _in_bounds(self, pos: Vector) -> bool:
        return all(e in range(BOARD_SIZE) for e in pos)

    def _can_jump_past_opponent(self, from_pos: Vector, opponent_pos: Vector) -> Vector | None:
        move = opponent_pos - from_pos
        target = opponent_pos + move
        jump_requirements = [
            self._in_bounds(target),
            not self.is_blocked(from_pos, opponent_pos),
            not self.is_blocked(opponent_pos, target),
        ]
        return target if all(jump_requirements) else None

    def _diagonal_jump_targets(self, from_pos: Vector, opponent_pos: Vector) -> Iterator[Vector]:
        move = opponent_pos - from_pos
        if move.y != 0 and move.x == 0:  # vertical
            left = Vector(opponent_pos.x, opponent_pos.y - 1)
            right = Vector(opponent_pos.x, opponent_pos.y + 1)
            for target in (left, right):
                if self.can_move(opponent_pos, target):
                    yield target
        elif move.x != 0 and move.y == 0:  # horizontal
            up = Vector(opponent_pos.x - 1, opponent_pos.y)
            down = Vector(opponent_pos.x + 1, opponent_pos.y)
            for target in (up, down):
                if self.can_move(opponent_pos, target):
                    yield target

    def _generate_pawn_moves_in_direction(
        self,
        current_pos: Vector,
        opponent_pos: Vector,
        move: Vector,
    ) -> Iterator[Move]:
        next_pos = current_pos + move
        if not self.can_move(current_pos, next_pos):
            return
        if next_pos != opponent_pos:
            yield (MoveType.MOVE, next_pos)
            return

        straight = self._can_jump_past_opponent(current_pos, next_pos)
        if straight is not None:
            yield (MoveType.MOVE, straight)
            return

        diagonals = self._diagonal_jump_targets(current_pos, next_pos)
        yield from ((MoveType.MOVE, target) for target in diagonals)

    def get_legal_moves(self) -> list[Move]:
        moves: list[Move] = []
        current_pos = self.get_player_pos(self.turn)
        opponent_pos = self.get_player_pos(self.turn.opponent)
        for move in map(Vector.from_tuple, ((-1, 0), (1, 0), (0, -1), (0, 1))):
            moves.extend(self._generate_pawn_moves_in_direction(current_pos, opponent_pos, move))

        walls_left = self.light_walls_left if self.turn == Player.LIGHT else self.dark_walls_left
        if walls_left > 0:
            for wr in range(BOARD_SIZE - 1):
                for wc in range(BOARD_SIZE - 1):
                    for orient in Orientation:
                        wall: Wall = (Vector(wr, wc), orient)
                        if self.is_valid_wall(wall) and self.path_exists_after_wall(wall):
                            moves.append((MoveType.WALL, wall))
        return moves

    def is_valid_wall(self, wall: Wall) -> bool:
        (r, c), orient = wall
        if wall in self.walls:
            return False

        # Check crossing
        opp_orient = Orientation.VERTICAL if orient == Orientation.HORIZONTAL else Orientation.HORIZONTAL
        if ((r, c), opp_orient) in self.walls:
            return False

        # Check overlapping tails
        if orient == Orientation.HORIZONTAL:
            if ((r, c - 1), Orientation.HORIZONTAL) in self.walls:
                return False
            if ((r, c + 1), Orientation.HORIZONTAL) in self.walls:
                return False
        else:
            if ((r - 1, c), Orientation.VERTICAL) in self.walls:
                return False
            if ((r + 1, c), Orientation.VERTICAL) in self.walls:
                return False
        return True

    def path_exists_after_wall(self, wall: Wall) -> bool:
        self.walls.add(wall)
        light_path = self.shortest_path_len(Player.LIGHT)
        dark_path = self.shortest_path_len(Player.DARK)
        self.walls.remove(wall)
        return light_path < MAX_PATH_COST and dark_path < MAX_PATH_COST
