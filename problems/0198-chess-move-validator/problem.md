# Chess Move Validator

## Statement

Design the rules engine behind a chess board. It loads a position, tells the players which moves are legal, applies legal moves, and reports when a move gives check, checkmate or stalemate. The engine must know every piece's movement, that a move may never leave the mover's own king in check, castling, en passant and promotion.

Implement the facade class `ChessGame`. There is no clock and no draw rule other than stalemate.

## Input

- `ChessGame(fen)`: loads a position written in Forsyth-Edwards Notation (FEN). Only its first four fields are used: piece placement, side to move (`w` or `b`), castling rights (any of `KQkq`, or `-`) and the en passant target square (or `-`). Further fields, if present, are ignored.
- `move(source, target)`: the side to move moves the piece on `source` to `target`. Squares are written as a file `a` to `h` and a rank `1` to `8`, for example `e4`. Castling is written as the king's move (`e1` to `g1`, for instance).
- `pieceAt(square)`: what stands on a square.
- `turn()`: the side to move.
- `legalMoves(square)`: every square the piece on `square` can legally move to.
- `inCheck()`: whether the side to move is in check.

Rules (standard chess):

- King one square in any direction; queen, rook and bishop any distance along open lines; knight in an L shape, jumping over pieces; pawn one square forward to an empty square, two from its starting rank when both squares are empty, and one square diagonally forward to capture.
- No piece may move onto a piece of its own color, and no move may leave the mover's king attacked.
- Castling: the king moves two squares towards a rook. It requires the matching castling right, that rook on its original square, empty squares between them, and that the king is not in check and does not pass through or land on an attacked square. The rook jumps to the square the king passed over. A right is lost forever when the king moves, when that rook moves, or when anything moves to the rook's original square.
- En passant: right after an opponent's pawn advanced two squares, a pawn beside it may capture it by moving diagonally onto the square it skipped. The chance is lost after any other move.
- A pawn that reaches the last rank always becomes a queen.

## Output

- `move` returns `"ILLEGAL"` (nothing changes) when a square is malformed, there is no piece of the side to move on `source`, or the move breaks a rule. Otherwise it applies the move, passes the turn, and returns `"CHECKMATE"` or `"STALEMATE"` when the new side to move has no legal move (in check or not), else `"CHECK"` or `"OK"`.
- `pieceAt` returns the color (`w` or `b`) followed by the piece letter in capitals (`K`, `Q`, `R`, `B`, `N`, `P`), for example `"wN"`, or `""` for an empty or malformed square.
- `turn` returns `"WHITE"` or `"BLACK"`.
- `legalMoves` returns the target squares in ascending string order, or an empty list when the square holds no piece of the side to move.

## Examples

### Example 1

<!-- case: ex1 -->

The classic four-move mate. The queen captures on `f7` protected by the bishop on `c4`, so the black king cannot take it, nothing can capture or block, and every escape square is covered: checkmate. Black is to move but has no legal move.

### Example 2

<!-- case: ex2 -->

With both rooks at home and all rights, the white king may castle either way, which adds `c1` and `g1` to its five ordinary moves. Castling on the king's side moves the rook from `h1` to `f1`; black then castles on the queen's side and its rook lands on `d8`.

## Constraints

- The position is legal: one king per side, the side not to move is not in check, and castling rights and the en passant square are consistent with the placement.
- At most 200 calls per test.

## Follow-ups

- How would you support promotion to a knight, rook or bishop without breaking `move(source, target)`?
- How would you detect draws by threefold repetition or the fifty-move rule?

## Hints

### Hint 1

Generate each piece's candidate moves with one rule object per piece type: steps (knight, king), slides along rays (bishop, rook, queen), and the pawn's special cases.

### Hint 2

Legality is "make the move on a copy, then ask whether the mover's king is attacked". Attack detection looks outward from the king's square: knight jumps, pawn captures, the adjacent king, and the first piece along each line.

### Hint 3

Keep positions immutable: a move returns a new position with the board, the side to move, the castling rights and the en passant square all updated in one place.
