# Chess Move Validator: Rubric

## Responsibilities

- [ ] A position owns the board, the side to move, the castling rights and the en passant square, and knows how to apply a move.
- [ ] Each piece type's movement lives in one rule object; no single method switches over every piece type to generate moves.
- [ ] Attack detection ("is this square attacked by that color?") is one function used for check, castling and legality alike.
- [ ] The facade turns square names into coordinates and classifies results; it holds no movement rules.

## Extension points

- [ ] A fairy piece or a rule variant (for example a piece that moves like a knight and a bishop) is a new rule object composed from existing step and slide rules.
- [ ] Choosing the promotion piece changes the move representation and `play`, not the piece rules.
- [ ] Draw rules (repetition, fifty moves) can be added from the sequence of immutable positions without touching move generation.

## Patterns

- [ ] Strategy per piece type: pawn, knight, bishop, rook, queen and king rules share one `targets(position, square)` interface.
- [ ] Positions are immutable values: a move produces a new position, which makes "try the move and test the king" trivial and side-effect free.
- [ ] Legal moves are pseudo-legal moves filtered by king safety, instead of special-casing pins and checks.

## Testability

- [ ] Any position can be loaded from FEN, so every rule (castling, en passant, pins, stalemate) gets a focused test without playing a game to reach it.
- [ ] `legalMoves` and `inCheck` expose the engine's reasoning, not just the final verdict of `move`.
- [ ] The engine is deterministic: there is no clock, randomness or I/O.

## Reference design

```text
ChessGame (facade: parsing, legality filter, result classification)
 └── Position (immutable): cells[64], side, castling rights, en passant square
       at(), attacked(square, by), inCheck(color), play(source, target) -> Position
Rules: PawnRule, StepRule(knight steps), SlideRule(rays) for B/R/Q, KingRule = StepRule + castling
```

`ChessGame.move` parses both squares, asks the rule of the piece on `source` for its candidate targets, keeps those whose resulting position leaves the mover's king safe, and applies the move if the target is among them. It then checks the new side to move: in check or not, with or without a legal move, which gives the four results.

`Position.play` does every side effect of a move in one place: it moves the piece, removes a pawn taken en passant, jumps the rook when the king castles, promotes a pawn on the last rank, removes castling rights touched by the move, records the en passant square after a double step, and flips the side. Because it returns a new position, the legality filter can call it freely.

`Position.attacked` looks outward from the target square: pawn capture squares, knight jumps, adjacent squares for the king, and the first piece along each orthogonal and diagonal line. Castling uses it for the squares the king crosses. Trade-offs: copying a 64-cell array per candidate move is cheap and keeps the code obviously correct; engines that search millions of positions use make-and-unmake on one mutable board, or bitboards, which are faster but much harder to get right in an interview.
