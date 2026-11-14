from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, replace

WHITE, BLACK = "w", "b"
KNIGHT_STEPS = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))
KING_STEPS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))
ORTHOGONAL = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIAGONAL = ((1, 1), (1, -1), (-1, 1), (-1, -1))
FILES = "abcdefgh"


def opponent(color: str) -> str:
    return BLACK if color == WHITE else WHITE


@dataclass(frozen=True, slots=True)
class Square:
    file: int
    rank: int

    @staticmethod
    def parse(text: str) -> Square | None:
        if len(text) != 2 or text[0] not in FILES or text[1] not in "12345678":
            return None
        return Square(FILES.index(text[0]), int(text[1]) - 1)

    def offset(self, files: int, ranks: int) -> Square | None:
        file, rank = self.file + files, self.rank + ranks
        return Square(file, rank) if 0 <= file < 8 and 0 <= rank < 8 else None

    @property
    def name(self) -> str:
        return f"{FILES[self.file]}{self.rank + 1}"


@dataclass(frozen=True, slots=True)
class Piece:
    color: str
    kind: str  # P, N, B, R, Q or K

    @property
    def code(self) -> str:
        return self.color + self.kind


@dataclass(frozen=True, slots=True)
class Position:
    """An immutable snapshot: pieces, side to move, castling rights and the en passant square."""

    cells: tuple[Piece | None, ...]  # index rank * 8 + file
    side: str
    castling: frozenset[str]  # subset of "KQkq"
    en_passant: Square | None

    @staticmethod
    def from_fen(fen: str) -> Position:
        placement, side, castling, en_passant = fen.split()[:4]
        cells: list[Piece | None] = [None] * 64
        for row, text in enumerate(placement.split("/")):
            file = 0
            for char in text:
                if char.isdigit():
                    file += int(char)
                    continue
                color = WHITE if char.isupper() else BLACK
                cells[(7 - row) * 8 + file] = Piece(color, char.upper())
                file += 1
        rights = frozenset() if castling == "-" else frozenset(castling)
        return Position(tuple(cells), side, rights, Square.parse(en_passant))

    def at(self, square: Square) -> Piece | None:
        return self.cells[square.rank * 8 + square.file]

    def is_enemy(self, square: Square, color: str) -> bool:
        piece = self.at(square)
        return piece is not None and piece.color != color

    def king(self, color: str) -> Square:
        index = self.cells.index(Piece(color, "K"))
        return Square(index % 8, index // 8)

    def in_check(self, color: str) -> bool:
        return self.attacked(self.king(color), opponent(color))

    def attacked(self, square: Square, by: str) -> bool:
        """Whether any piece of `by` attacks `square` (pawns by their capture direction)."""
        forward = 1 if by == WHITE else -1
        for files in (-1, 1):
            origin = square.offset(files, -forward)
            if origin is not None and self.at(origin) == Piece(by, "P"):
                return True
        for kind, steps in (("N", KNIGHT_STEPS), ("K", KING_STEPS)):
            for step in steps:
                origin = square.offset(*step)
                if origin is not None and self.at(origin) == Piece(by, kind):
                    return True
        for kinds, rays in (({"R", "Q"}, ORTHOGONAL), ({"B", "Q"}, DIAGONAL)):
            for ray in rays:
                piece = self.first_piece(square, ray)
                if piece is not None and piece.color == by and piece.kind in kinds:
                    return True
        return False

    def first_piece(self, start: Square, direction: tuple[int, int]) -> Piece | None:
        for square in self.ray(start, direction):
            if (piece := self.at(square)) is not None:
                return piece
        return None

    def ray(self, start: Square, direction: tuple[int, int]) -> Iterator[Square]:
        """Squares along `direction` up to and including the first occupied one."""
        square = start.offset(*direction)
        while square is not None:
            yield square
            if self.at(square) is not None:
                return
            square = square.offset(*direction)

    def play(self, source: Square, target: Square) -> Position:
        """The position after moving the piece on `source` to `target` (assumed pseudo-legal)."""
        piece = self.at(source)
        cells = list(self.cells)
        cells[source.rank * 8 + source.file] = None
        if piece.kind == "P" and target == self.en_passant:
            cells[source.rank * 8 + target.file] = None  # the pawn captured en passant
        if piece.kind == "K" and abs(target.file - source.file) == 2:
            rook_from, rook_to = (7, 5) if target.file == 6 else (0, 3)
            cells[source.rank * 8 + rook_to] = cells[source.rank * 8 + rook_from]
            cells[source.rank * 8 + rook_from] = None
        last_rank = 7 if piece.color == WHITE else 0
        promoted = piece.kind == "P" and target.rank == last_rank
        cells[target.rank * 8 + target.file] = Piece(piece.color, "Q") if promoted else piece
        double_push = piece.kind == "P" and abs(target.rank - source.rank) == 2
        passed = Square(source.file, (source.rank + target.rank) // 2) if double_push else None
        return replace(
            self,
            cells=tuple(cells),
            side=opponent(self.side),
            castling=self.castling - _rights_lost(piece, source, target),
            en_passant=passed,
        )


ROOK_HOMES = {Square(0, 0): "Q", Square(7, 0): "K", Square(0, 7): "q", Square(7, 7): "k"}


def _rights_lost(piece: Piece, source: Square, target: Square) -> set[str]:
    lost = {ROOK_HOMES[square] for square in (source, target) if square in ROOK_HOMES}
    if piece.kind == "K":
        lost |= {"K", "Q"} if piece.color == WHITE else {"k", "q"}
    return lost


class StepRule:
    def __init__(self, steps: tuple[tuple[int, int], ...]) -> None:
        self._steps = steps

    def targets(self, position: Position, square: Square, color: str) -> Iterator[Square]:
        for step in self._steps:
            target = square.offset(*step)
            if target is not None and (position.at(target) is None or position.is_enemy(target, color)):
                yield target


class SlideRule:
    def __init__(self, rays: tuple[tuple[int, int], ...]) -> None:
        self._rays = rays

    def targets(self, position: Position, square: Square, color: str) -> Iterator[Square]:
        for ray in self._rays:
            for target in position.ray(square, ray):
                if position.at(target) is None or position.is_enemy(target, color):
                    yield target


class KingRule(StepRule):
    def __init__(self) -> None:
        super().__init__(KING_STEPS)

    def targets(self, position: Position, square: Square, color: str) -> Iterator[Square]:
        yield from super().targets(position, square, color)
        yield from self._castling(position, square, color)

    @staticmethod
    def _castling(position: Position, square: Square, color: str) -> Iterator[Square]:
        rank = 0 if color == WHITE else 7
        if square != Square(4, rank) or position.attacked(square, opponent(color)):
            return
        # right, rook file, files that must be empty, files the king crosses or lands on
        sides = (("K", 7, (5, 6), (5, 6)), ("Q", 0, (1, 2, 3), (3, 2)))
        for right, rook_file, empty, crossed in sides:
            letter = right if color == WHITE else right.lower()
            if letter not in position.castling or position.at(Square(rook_file, rank)) != Piece(color, "R"):
                continue
            if any(position.at(Square(file, rank)) is not None for file in empty):
                continue
            if any(position.attacked(Square(file, rank), opponent(color)) for file in crossed):
                continue
            yield Square(crossed[-1], rank)


class PawnRule:
    def targets(self, position: Position, square: Square, color: str) -> Iterator[Square]:
        forward = 1 if color == WHITE else -1
        one = square.offset(0, forward)
        if one is not None and position.at(one) is None:
            yield one
            two = square.offset(0, 2 * forward)
            start_rank = 1 if color == WHITE else 6
            if square.rank == start_rank and two is not None and position.at(two) is None:
                yield two
        for files in (-1, 1):
            target = square.offset(files, forward)
            if target is not None and (position.is_enemy(target, color) or target == position.en_passant):
                yield target


RULES = {
    "P": PawnRule(),
    "N": StepRule(KNIGHT_STEPS),
    "B": SlideRule(DIAGONAL),
    "R": SlideRule(ORTHOGONAL),
    "Q": SlideRule(ORTHOGONAL + DIAGONAL),
    "K": KingRule(),
}


class ChessGame:
    def __init__(self, fen: str) -> None:
        self._position = Position.from_fen(fen)

    def move(self, source: str, target: str) -> str:
        start, end = Square.parse(source), Square.parse(target)
        if start is None or end is None or end not in self._legal_targets(start):
            return "ILLEGAL"
        self._position = self._position.play(start, end)
        side = self._position.side
        in_check = self._position.in_check(side)
        if not self._has_legal_move():
            return "CHECKMATE" if in_check else "STALEMATE"
        return "CHECK" if in_check else "OK"

    def piece_at(self, square: str) -> str:
        parsed = Square.parse(square)
        piece = None if parsed is None else self._position.at(parsed)
        return "" if piece is None else piece.code

    def turn(self) -> str:
        return "WHITE" if self._position.side == WHITE else "BLACK"

    def legal_moves(self, square: str) -> list[str]:
        parsed = Square.parse(square)
        return [] if parsed is None else sorted(target.name for target in self._legal_targets(parsed))

    def in_check(self) -> bool:
        return self._position.in_check(self._position.side)

    def _legal_targets(self, square: Square) -> list[Square]:
        """Pseudo-legal targets that do not leave the mover's own king attacked."""
        position = self._position
        piece = position.at(square)
        if piece is None or piece.color != position.side:
            return []
        candidates = RULES[piece.kind].targets(position, square, piece.color)
        return [target for target in candidates if not position.play(square, target).in_check(piece.color)]

    def _has_legal_move(self) -> bool:
        return any(
            self._legal_targets(Square(index % 8, index // 8))
            for index, piece in enumerate(self._position.cells)
            if piece is not None and piece.color == self._position.side
        )
