type Color = "w" | "b";
type Kind = "P" | "N" | "B" | "R" | "Q" | "K";
type Step = readonly [files: number, ranks: number];

interface Piece {
  readonly color: Color;
  readonly kind: Kind;
}

const FILES = "abcdefgh";
const KNIGHT_STEPS: readonly Step[] = [[1, 2], [2, 1], [2, -1], [1, -2], [-1, -2], [-2, -1], [-2, 1], [-1, 2]];
const KING_STEPS: readonly Step[] = [[1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1]];
const ORTHOGONAL: readonly Step[] = [[1, 0], [-1, 0], [0, 1], [0, -1]];
const DIAGONAL: readonly Step[] = [[1, 1], [1, -1], [-1, 1], [-1, -1]];
const ROOK_HOMES = new Map<number, string>([[0, "Q"], [7, "K"], [56, "q"], [63, "k"]]);

// Squares are indexes rank * 8 + file, from a1 = 0 to h8 = 63.
function parseSquare(text: string): number | null {
  if (text.length !== 2 || !FILES.includes(text[0]) || !"12345678".includes(text[1])) {
    return null;
  }
  return (Number(text[1]) - 1) * 8 + FILES.indexOf(text[0]);
}

function fileOf(square: number): number {
  return square % 8;
}

function rankOf(square: number): number {
  return Math.floor(square / 8);
}

function offset(square: number, [files, ranks]: Step): number | null {
  const file = fileOf(square) + files;
  const rank = rankOf(square) + ranks;
  return file >= 0 && file < 8 && rank >= 0 && rank < 8 ? rank * 8 + file : null;
}

function nameOf(square: number): string {
  return `${FILES[fileOf(square)]}${rankOf(square) + 1}`;
}

function opponent(color: Color): Color {
  return color === "w" ? "b" : "w";
}

function isPiece(piece: Piece | null, color: Color, kind: Kind): boolean {
  return piece !== null && piece.color === color && piece.kind === kind;
}

// An immutable snapshot: pieces, side to move, castling rights and the en passant square.
class Position {
  readonly cells: readonly (Piece | null)[];
  readonly side: Color;
  readonly castling: ReadonlySet<string>;
  readonly enPassant: number | null;

  constructor(cells: readonly (Piece | null)[], side: Color, castling: ReadonlySet<string>, enPassant: number | null) {
    this.cells = cells;
    this.side = side;
    this.castling = castling;
    this.enPassant = enPassant;
  }

  static fromFen(fen: string): Position {
    const [placement, side, castling, enPassant] = fen.split(" ");
    const cells: (Piece | null)[] = new Array(64).fill(null);
    placement.split("/").forEach((row, index) => {
      let file = 0;
      for (const char of row) {
        if (char >= "1" && char <= "8") {
          file += Number(char);
          continue;
        }
        const color: Color = char === char.toUpperCase() ? "w" : "b";
        cells[(7 - index) * 8 + file] = { color, kind: char.toUpperCase() as Kind };
        file++;
      }
    });
    const rights = new Set(castling === "-" ? [] : [...castling]);
    return new Position(cells, side === "w" ? "w" : "b", rights, parseSquare(enPassant));
  }

  at(square: number): Piece | null {
    return this.cells[square];
  }

  isFreeFor(square: number, color: Color): boolean {
    const piece = this.at(square);
    return piece === null || piece.color !== color;
  }

  inCheck(color: Color): boolean {
    const king = this.cells.findIndex((piece) => isPiece(piece, color, "K"));
    return this.attacked(king, opponent(color));
  }

  // Whether any piece of `by` attacks `square` (pawns by their capture direction).
  attacked(square: number, by: Color): boolean {
    const forward = by === "w" ? 1 : -1;
    for (const files of [-1, 1]) {
      const origin = offset(square, [files, -forward]);
      if (origin !== null && isPiece(this.at(origin), by, "P")) {
        return true;
      }
    }
    for (const [kind, steps] of [["N", KNIGHT_STEPS], ["K", KING_STEPS]] as const) {
      for (const step of steps) {
        const origin = offset(square, step);
        if (origin !== null && isPiece(this.at(origin), by, kind)) {
          return true;
        }
      }
    }
    for (const [kinds, rays] of [[["R", "Q"], ORTHOGONAL], [["B", "Q"], DIAGONAL]] as const) {
      for (const ray of rays) {
        const piece = this.firstPiece(square, ray);
        if (piece !== null && piece.color === by && (kinds as readonly Kind[]).includes(piece.kind)) {
          return true;
        }
      }
    }
    return false;
  }

  // Squares along `direction` up to and including the first occupied one.
  ray(start: number, direction: Step): number[] {
    const squares: number[] = [];
    for (let square = offset(start, direction); square !== null; square = offset(square, direction)) {
      squares.push(square);
      if (this.at(square) !== null) {
        break;
      }
    }
    return squares;
  }

  firstPiece(start: number, direction: Step): Piece | null {
    const squares = this.ray(start, direction);
    return squares.length === 0 ? null : this.at(squares[squares.length - 1]);
  }

  // The position after moving the piece on `source` to `target` (assumed pseudo-legal).
  play(source: number, target: number): Position {
    const piece = this.at(source);
    if (piece === null) {
      return this;
    }
    const cells = [...this.cells];
    const rank = rankOf(source);
    cells[source] = null;
    if (piece.kind === "P" && target === this.enPassant) {
      cells[rank * 8 + fileOf(target)] = null; // the pawn captured en passant
    }
    if (piece.kind === "K" && Math.abs(fileOf(target) - fileOf(source)) === 2) {
      const [rookFrom, rookTo] = fileOf(target) === 6 ? [7, 5] : [0, 3];
      cells[rank * 8 + rookTo] = cells[rank * 8 + rookFrom];
      cells[rank * 8 + rookFrom] = null;
    }
    const lastRank = piece.color === "w" ? 7 : 0;
    const promoted = piece.kind === "P" && rankOf(target) === lastRank;
    cells[target] = promoted ? { color: piece.color, kind: "Q" } : piece;
    const doublePush = piece.kind === "P" && Math.abs(rankOf(target) - rank) === 2;
    const castling = new Set(this.castling);
    for (const square of [source, target]) {
      const right = ROOK_HOMES.get(square);
      if (right !== undefined) {
        castling.delete(right);
      }
    }
    if (piece.kind === "K") {
      for (const right of piece.color === "w" ? ["K", "Q"] : ["k", "q"]) {
        castling.delete(right);
      }
    }
    return new Position(cells, opponent(this.side), castling, doublePush ? (source + target) / 2 : null);
  }
}

interface MoveRule {
  targets(position: Position, square: number, color: Color): number[];
}

class StepRule implements MoveRule {
  private readonly steps: readonly Step[];

  constructor(steps: readonly Step[]) {
    this.steps = steps;
  }

  targets(position: Position, square: number, color: Color): number[] {
    return this.steps
      .map((step) => offset(square, step))
      .filter((target): target is number => target !== null && position.isFreeFor(target, color));
  }
}

class SlideRule implements MoveRule {
  private readonly rays: readonly Step[];

  constructor(rays: readonly Step[]) {
    this.rays = rays;
  }

  targets(position: Position, square: number, color: Color): number[] {
    return this.rays.flatMap((ray) => position.ray(square, ray).filter((target) => position.isFreeFor(target, color)));
  }
}

class KingRule extends StepRule {
  constructor() {
    super(KING_STEPS);
  }

  override targets(position: Position, square: number, color: Color): number[] {
    return [...super.targets(position, square, color), ...KingRule.castling(position, square, color)];
  }

  private static castling(position: Position, square: number, color: Color): number[] {
    const rank = color === "w" ? 0 : 7;
    if (square !== rank * 8 + 4 || position.attacked(square, opponent(color))) {
      return [];
    }
    // right, rook file, files that must be empty, files the king crosses or lands on
    const sides = [["K", 7, [5, 6], [5, 6]], ["Q", 0, [1, 2, 3], [3, 2]]] as const;
    const targets: number[] = [];
    for (const [right, rookFile, empty, crossed] of sides) {
      const letter = color === "w" ? right : right.toLowerCase();
      if (!position.castling.has(letter) || !isPiece(position.at(rank * 8 + rookFile), color, "R")) {
        continue;
      }
      if (empty.some((file) => position.at(rank * 8 + file) !== null)) {
        continue;
      }
      if (crossed.some((file) => position.attacked(rank * 8 + file, opponent(color)))) {
        continue;
      }
      targets.push(rank * 8 + crossed[crossed.length - 1]);
    }
    return targets;
  }
}

class PawnRule implements MoveRule {
  targets(position: Position, square: number, color: Color): number[] {
    const forward = color === "w" ? 1 : -1;
    const targets: number[] = [];
    const one = offset(square, [0, forward]);
    if (one !== null && position.at(one) === null) {
      targets.push(one);
      const two = offset(square, [0, 2 * forward]);
      const startRank = color === "w" ? 1 : 6;
      if (rankOf(square) === startRank && two !== null && position.at(two) === null) {
        targets.push(two);
      }
    }
    for (const files of [-1, 1]) {
      const target = offset(square, [files, forward]);
      if (target === null) {
        continue;
      }
      const piece = position.at(target);
      if ((piece !== null && piece.color !== color) || target === position.enPassant) {
        targets.push(target);
      }
    }
    return targets;
  }
}

const RULES: Record<Kind, MoveRule> = {
  P: new PawnRule(),
  N: new StepRule(KNIGHT_STEPS),
  B: new SlideRule(DIAGONAL),
  R: new SlideRule(ORTHOGONAL),
  Q: new SlideRule([...ORTHOGONAL, ...DIAGONAL]),
  K: new KingRule(),
};

export class ChessGame {
  private position: Position;

  constructor(fen: string) {
    this.position = Position.fromFen(fen);
  }

  move(source: string, target: string): string {
    const start = parseSquare(source);
    const end = parseSquare(target);
    if (start === null || end === null || !this.legalTargets(start).includes(end)) {
      return "ILLEGAL";
    }
    this.position = this.position.play(start, end);
    const inCheck = this.position.inCheck(this.position.side);
    if (!this.hasLegalMove()) {
      return inCheck ? "CHECKMATE" : "STALEMATE";
    }
    return inCheck ? "CHECK" : "OK";
  }

  pieceAt(square: string): string {
    const parsed = parseSquare(square);
    const piece = parsed === null ? null : this.position.at(parsed);
    return piece === null ? "" : piece.color + piece.kind;
  }

  turn(): string {
    return this.position.side === "w" ? "WHITE" : "BLACK";
  }

  legalMoves(square: string): string[] {
    const parsed = parseSquare(square);
    return parsed === null ? [] : this.legalTargets(parsed).map(nameOf).sort();
  }

  inCheck(): boolean {
    return this.position.inCheck(this.position.side);
  }

  // Pseudo-legal targets that do not leave the mover's own king attacked.
  private legalTargets(square: number): number[] {
    const position = this.position;
    const piece = position.at(square);
    if (piece === null || piece.color !== position.side) {
      return [];
    }
    return RULES[piece.kind]
      .targets(position, square, piece.color)
      .filter((target) => !position.play(square, target).inCheck(piece.color));
  }

  private hasLegalMove(): boolean {
    return this.position.cells.some(
      (piece, square) => piece !== null && piece.color === this.position.side && this.legalTargets(square).length > 0,
    );
  }
}
