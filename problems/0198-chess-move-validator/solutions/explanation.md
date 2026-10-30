# Chess Move Validator: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| rule-per-piece | optimal | O(m) per legality check; O(p m) per move to classify the result | O(1) per position | default answer; every chess rule has exactly one home |

Here `m` is the number of candidate moves of one piece (at most 27, for a queen) and `p` the number of pieces of the side to move. The board has a fixed 64 squares, so a position is O(1) space and each attack check is O(1) work, bounded by the board size.

## Approach: rule-per-piece (Immutable positions with one move rule per piece)

### Intuition

Chess legality splits cleanly in two. First, how each piece moves on an empty-ish board: steps for the knight and king, slides along rays for bishop, rook and queen, and the pawn's special cases. These are pseudo-legal moves. Second, one rule that overrides all of them: you may not leave your own king attacked. Instead of reasoning about pins and checks directly, try each pseudo-legal move on a copy of the position and ask whether the king is attacked afterwards. Pins, discovered checks, moving into check and answering a check all fall out of that single test.

Making positions immutable makes "try it on a copy" natural: `play` returns a new position and never disturbs the current one. All the bookkeeping of a move (captures, en passant removal, the rook's jump in castling, promotion, castling rights, the next en passant square, the side to move) lives in that one method.

### Algorithm

1. `fromFen`: read the placement row by row from rank 8, digits meaning empty squares; read the side, the castling letters and the en passant square.
2. `attacked(square, by)`: look outward from `square`: two pawn capture squares (behind it from `by`'s point of view), the eight knight jumps, the eight king steps, and the first piece along each orthogonal ray (rook or queen) and each diagonal ray (bishop or queen).
3. Candidate moves per piece:
   1. Step rules (knight, king): each step that stays on the board and does not land on an own piece.
   2. Slide rules (bishop, rook, queen): along each ray, every empty square plus the first piece if it is an enemy.
   3. Pawn: one step forward to an empty square; two from the starting rank when both are empty; diagonal steps onto an enemy or onto the en passant square.
   4. King, additionally castling: for each side whose right is present and whose rook is home, the squares between must be empty, and the king's square, the square it crosses and the square it lands on must not be attacked.
4. Legal targets of a square: the candidates of its piece (if it belongs to the side to move) whose resulting position does not have the mover's king attacked.
5. `play(source, target)`: move the piece; on an en passant capture remove the pawn beside the source; on castling move the rook from the corner to the square the king crossed; promote a pawn on the last rank to a queen; drop castling rights for a king move and for any move from or to a rook's home square; set the en passant square after a double step; flip the side.
6. `move`: illegal unless the target is a legal target of the source. After playing, the opponent with no legal move is checkmated if in check and stalemated otherwise; with moves, the result is `CHECK` or `OK`.

### Correctness

Every legal chess move is a pseudo-legal move of its piece that leaves the king safe, and every move that passes both tests is legal: the candidate rules produce exactly the standard movements, and the safety test applies the one rule that restricts them. Castling has extra conditions about attacked squares that the safety test alone would miss (crossing an attacked square), so the king rule checks them before offering the move; the safety test then confirms the landing square.

Attack detection is complete because every way a piece can attack a square is symmetric: a knight on `x` attacks `y` exactly when a knight's jump from `y` reaches `x`, and a slider attacks along a line only if it is the first piece on that line. Pawns are the one asymmetric piece, which is why their capture squares are looked up backwards, from `by`'s direction.

Castling rights only ever shrink: a king move removes both rights of its color, and any move touching a rook's home square removes that square's right, which covers the rook moving away and the rook being captured there. The en passant square is set only by a double step and cleared by every other move, so the capture is available exactly on the next move.

### Complexity

- Time: O(m) per legality check; O(p m) per move to classify the result — each candidate costs a copy of 64 cells and one attack test of bounded size; deciding checkmate or stalemate asks every piece of the new side to move for at least one legal move.
- Space: O(1) per position — 64 cells and a few fields; the legality filter creates short-lived copies.

### Trade-offs

- Copying the board per candidate is simple and clearly correct. Engines that search deeply use make-and-unmake on a single mutable board, or bitboards with precomputed attack tables, which are much faster and much easier to get wrong.
- Computing pins and check rays directly (only king moves, captures of the checker, or interpositions are legal in check) avoids the trial moves, but needs separate logic for pins, double checks and en passant discoveries. The trial-move filter handles all of them uniformly.
- Promotion always to a queen keeps the API at two squares. Supporting under-promotion needs a third argument or a move string such as `e7e8n`, and changes only `play` and the parser.
- `legalMoves` lists target squares, not full moves; with under-promotion several moves would share a target, which is another reason a richer move type appears in real engines.

### Pitfalls and edge cases

- Sliding attacks need the first occupied square along the ray, not the first square; an empty first square does not stop the ray.
- The castling king may not be in check, pass through an attacked square or land on one; the rook's crossing square on the queen's side (`b1`) must be empty but may be attacked.
- Capturing a rook on its home square removes the opponent's castling right on that side.
- En passant removes the pawn beside the moving pawn, not the one on the target square, and can expose the mover's king along the rank; the trial-move filter catches that.
- A pinned piece may still move along the pin line, including capturing the pinning piece.
- After checkmate or stalemate the side to move has no legal move, so every further move is `ILLEGAL`.

### Language notes

- Python: frozen dataclasses for `Square`, `Piece` and `Position`, and `dataclasses.replace` to build the next position; generators yield ray squares lazily.
- TypeScript: squares are integers 0 to 63, because objects compare by reference; labelled tuple types (`[files: number, ranks: number]`) document the steps, and `Record<Kind, MoveRule>` maps pieces to their rules.
- Java: records `Square` and `Piece` give value equality for free, which makes `target.equals(enPassant)` and map lookups correct; `Optional<Square>` models squares that fall off the board; `cells.clone()` copies the board.
- Kotlin: data classes for squares and pieces, `Pair<Int, Int>` steps with destructuring, a `fun interface MoveRule`, and an open `StepRule` that `KingRule` extends with castling.
- Go: `position` is a plain value holding a `[64]piece` array, and Go copies arrays on assignment, so `play` is `next := *p` plus a few writes: the immutable snapshots of the Python version without a copy helper. The zero `piece{}` is the empty square, `rights` is a bit set, and `kingRule` embeds `stepRule` and adds castling, which is how Go spells the Kotlin subclass. Rays are slices of squares, built up to the first occupied one.
- Rust: `move` is a keyword, so the method is the raw identifier `r#move`, as the stub declares it. `Position` is `Copy` (an `[Option<Piece>; 64]` array, the side to move, a castling bit set and the en passant square), so `play` starts from `let mut next = *self` and the snapshots stay immutable without a copy helper; `None` is the empty square. `MoveRule` is a trait and `rule_for` hands out `&'static dyn MoveRule` values from statics; `KingRule` calls a `StepRule` and adds castling, since a trait has no subclass. A slice pattern (`&[file @ b'a'..=b'h', rank @ b'1'..=b'8']`) parses a square, and `let ... else` returns `ILLEGAL` early.
