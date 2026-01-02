from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import NamedTuple

from quoridor.constants import BOARD_SIZE


class Orientation(StrEnum):
    HORIZONTAL = "h"
    VERTICAL = "v"


class MoveType(StrEnum):
    MOVE = "move"
    WALL = "wall"


type Wall = tuple[Vector, Orientation]
type Move = tuple[MoveType, Vector | Wall]


class Vector(NamedTuple):
    x: int
    y: int

    @classmethod
    def from_tuple(cls, xy_values: tuple[int, int]) -> Vector:
        return cls(*xy_values)

    def __add__(self, other: Vector) -> Vector:
        return Vector(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector) -> Vector:
        return Vector(self.x - other.x, self.y - other.y)

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"


class Player(IntEnum):
    LIGHT = 1  # Starts at row 0 (top)
    DARK = 2  # Starts at row 8 (bottom)

    @property
    def opponent(self) -> Player:
        return Player.DARK if self == Player.LIGHT else Player.LIGHT

    @property
    def goal_row(self) -> int:
        return BOARD_SIZE - 1 if self == Player.LIGHT else 0

    @property
    def symbol(self) -> str:
        return "L" if self == Player.LIGHT else "D"
