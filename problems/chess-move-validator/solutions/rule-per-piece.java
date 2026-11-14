import java.util.*;

public class ChessGame {
    private static final char WHITE = 'w';
    private static final char BLACK = 'b';
    private static final int[][] KNIGHT_STEPS = {{1, 2}, {2, 1}, {2, -1}, {1, -2}, {-1, -2}, {-2, -1}, {-2, 1}, {-1, 2}};
    private static final int[][] KING_STEPS = {{1, 0}, {1, 1}, {0, 1}, {-1, 1}, {-1, 0}, {-1, -1}, {0, -1}, {1, -1}};
    private static final int[][] ORTHOGONAL = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
    private static final int[][] DIAGONAL = {{1, 1}, {1, -1}, {-1, 1}, {-1, -1}};
    private static final String FILES = "abcdefgh";

    private static char opponent(char color) {
        return color == WHITE ? BLACK : WHITE;
    }

    private record Square(int file, int rank) {
        static Optional<Square> parse(String text) {
            if (text.length() != 2 || FILES.indexOf(text.charAt(0)) < 0 || text.charAt(1) < '1' || text.charAt(1) > '8') {
                return Optional.empty();
            }
            return Optional.of(new Square(FILES.indexOf(text.charAt(0)), text.charAt(1) - '1'));
        }

        Optional<Square> offset(int[] step) {
            int newFile = file + step[0];
            int newRank = rank + step[1];
            boolean inside = newFile >= 0 && newFile < 8 && newRank >= 0 && newRank < 8;
            return inside ? Optional.of(new Square(newFile, newRank)) : Optional.empty();
        }

        String name() {
            return "" + FILES.charAt(file) + (rank + 1);
        }
    }

    private record Piece(char color, char kind) {
        String code() {
            return "" + color + kind;
        }
    }

    private static final Map<Square, Character> ROOK_HOMES = Map.of(
            new Square(0, 0), 'Q', new Square(7, 0), 'K', new Square(0, 7), 'q', new Square(7, 7), 'k');

    /** An immutable snapshot: pieces, side to move, castling rights and the en passant square. */
    private static final class Position {
        private final Piece[] cells; // index rank * 8 + file; never mutated after construction
        final char side;
        final Set<Character> castling;
        final Square enPassant; // null when there is none

        Position(Piece[] cells, char side, Set<Character> castling, Square enPassant) {
            this.cells = cells;
            this.side = side;
            this.castling = Set.copyOf(castling);
            this.enPassant = enPassant;
        }

        static Position fromFen(String fen) {
            String[] fields = fen.split(" ");
            Piece[] cells = new Piece[64];
            String[] rows = fields[0].split("/");
            for (int row = 0; row < 8; row++) {
                int file = 0;
                for (char symbol : rows[row].toCharArray()) {
                    if (Character.isDigit(symbol)) {
                        file += symbol - '0';
                        continue;
                    }
                    char color = Character.isUpperCase(symbol) ? WHITE : BLACK;
                    cells[(7 - row) * 8 + file] = new Piece(color, Character.toUpperCase(symbol));
                    file++;
                }
            }
            Set<Character> rights = new HashSet<>();
            if (!fields[2].equals("-")) {
                fields[2].chars().forEach(right -> rights.add((char) right));
            }
            return new Position(cells, fields[1].charAt(0), rights, Square.parse(fields[3]).orElse(null));
        }

        Piece at(Square square) {
            return cells[square.rank() * 8 + square.file()];
        }

        boolean isFreeFor(Square square, char color) {
            Piece piece = at(square);
            return piece == null || piece.color() != color;
        }

        boolean inCheck(char color) {
            for (int index = 0; index < 64; index++) {
                if (new Piece(color, 'K').equals(cells[index])) {
                    return attacked(new Square(index % 8, index / 8), opponent(color));
                }
            }
            return false;
        }

        /** Whether any piece of {@code by} attacks {@code square} (pawns by their capture direction). */
        boolean attacked(Square square, char by) {
            int forward = by == WHITE ? 1 : -1;
            for (int files : new int[] {-1, 1}) {
                Optional<Square> origin = square.offset(new int[] {files, -forward});
                if (origin.isPresent() && new Piece(by, 'P').equals(at(origin.get()))) {
                    return true;
                }
            }
            if (attackedByStep(square, KNIGHT_STEPS, new Piece(by, 'N')) || attackedByStep(square, KING_STEPS, new Piece(by, 'K'))) {
                return true;
            }
            return attackedAlong(square, ORTHOGONAL, by, "RQ") || attackedAlong(square, DIAGONAL, by, "BQ");
        }

        private boolean attackedByStep(Square square, int[][] steps, Piece attacker) {
            for (int[] step : steps) {
                Optional<Square> origin = square.offset(step);
                if (origin.isPresent() && attacker.equals(at(origin.get()))) {
                    return true;
                }
            }
            return false;
        }

        private boolean attackedAlong(Square square, int[][] rays, char by, String kinds) {
            for (int[] ray : rays) {
                List<Square> line = ray(square, ray);
                Piece piece = line.isEmpty() ? null : at(line.get(line.size() - 1));
                if (piece != null && piece.color() == by && kinds.indexOf(piece.kind()) >= 0) {
                    return true;
                }
            }
            return false;
        }

        /** Squares along {@code direction} up to and including the first occupied one. */
        List<Square> ray(Square start, int[] direction) {
            List<Square> squares = new ArrayList<>();
            for (Optional<Square> next = start.offset(direction); next.isPresent(); next = next.get().offset(direction)) {
                squares.add(next.get());
                if (at(next.get()) != null) {
                    break;
                }
            }
            return squares;
        }

        /** The position after moving the piece on {@code source} to {@code target} (assumed pseudo-legal). */
        Position play(Square source, Square target) {
            Piece piece = at(source);
            Piece[] next = cells.clone();
            int rank = source.rank();
            next[rank * 8 + source.file()] = null;
            if (piece.kind() == 'P' && target.equals(enPassant)) {
                next[rank * 8 + target.file()] = null; // the pawn captured en passant
            }
            if (piece.kind() == 'K' && Math.abs(target.file() - source.file()) == 2) {
                int rookFrom = target.file() == 6 ? 7 : 0;
                int rookTo = target.file() == 6 ? 5 : 3;
                next[rank * 8 + rookTo] = next[rank * 8 + rookFrom];
                next[rank * 8 + rookFrom] = null;
            }
            int lastRank = piece.color() == WHITE ? 7 : 0;
            boolean promoted = piece.kind() == 'P' && target.rank() == lastRank;
            next[target.rank() * 8 + target.file()] = promoted ? new Piece(piece.color(), 'Q') : piece;
            Set<Character> rights = new HashSet<>(castling);
            for (Square square : List.of(source, target)) {
                Character right = ROOK_HOMES.get(square);
                if (right != null) {
                    rights.remove(right);
                }
            }
            if (piece.kind() == 'K') {
                rights.removeAll(piece.color() == WHITE ? Set.of('K', 'Q') : Set.of('k', 'q'));
            }
            boolean doublePush = piece.kind() == 'P' && Math.abs(target.rank() - rank) == 2;
            Square passed = doublePush ? new Square(source.file(), (rank + target.rank()) / 2) : null;
            return new Position(next, opponent(side), rights, passed);
        }
    }

    private interface MoveRule {
        List<Square> targets(Position position, Square square, char color);
    }

    private static class StepRule implements MoveRule {
        private final int[][] steps;

        StepRule(int[][] steps) {
            this.steps = steps;
        }

        public List<Square> targets(Position position, Square square, char color) {
            List<Square> targets = new ArrayList<>();
            for (int[] step : steps) {
                square.offset(step).filter(target -> position.isFreeFor(target, color)).ifPresent(targets::add);
            }
            return targets;
        }
    }

    private static final class SlideRule implements MoveRule {
        private final int[][] rays;

        SlideRule(int[][] rays) {
            this.rays = rays;
        }

        public List<Square> targets(Position position, Square square, char color) {
            List<Square> targets = new ArrayList<>();
            for (int[] ray : rays) {
                for (Square target : position.ray(square, ray)) {
                    if (position.isFreeFor(target, color)) {
                        targets.add(target);
                    }
                }
            }
            return targets;
        }
    }

    private static final class KingRule extends StepRule {
        KingRule() {
            super(KING_STEPS);
        }

        @Override
        public List<Square> targets(Position position, Square square, char color) {
            List<Square> targets = super.targets(position, square, color);
            int rank = color == WHITE ? 0 : 7;
            if (!square.equals(new Square(4, rank)) || position.attacked(square, opponent(color))) {
                return targets;
            }
            castle(position, color, rank, 'K', 7, new int[] {5, 6}, new int[] {5, 6}).ifPresent(targets::add);
            castle(position, color, rank, 'Q', 0, new int[] {1, 2, 3}, new int[] {3, 2}).ifPresent(targets::add);
            return targets;
        }

        /** The king's target square for one side's castling, if every condition holds. */
        private static Optional<Square> castle(
                Position position, char color, int rank, char right, int rookFile, int[] empty, int[] crossed) {
            char letter = color == WHITE ? right : Character.toLowerCase(right);
            if (!position.castling.contains(letter) || !new Piece(color, 'R').equals(position.at(new Square(rookFile, rank)))) {
                return Optional.empty();
            }
            for (int file : empty) {
                if (position.at(new Square(file, rank)) != null) {
                    return Optional.empty();
                }
            }
            for (int file : crossed) {
                if (position.attacked(new Square(file, rank), opponent(color))) {
                    return Optional.empty();
                }
            }
            return Optional.of(new Square(crossed[crossed.length - 1], rank));
        }
    }

    private static final class PawnRule implements MoveRule {
        public List<Square> targets(Position position, Square square, char color) {
            int forward = color == WHITE ? 1 : -1;
            int startRank = color == WHITE ? 1 : 6;
            List<Square> targets = new ArrayList<>();
            Optional<Square> one = square.offset(new int[] {0, forward});
            if (one.isPresent() && position.at(one.get()) == null) {
                targets.add(one.get());
                Optional<Square> two = square.offset(new int[] {0, 2 * forward});
                if (square.rank() == startRank && two.isPresent() && position.at(two.get()) == null) {
                    targets.add(two.get());
                }
            }
            for (int files : new int[] {-1, 1}) {
                Optional<Square> diagonal = square.offset(new int[] {files, forward});
                if (diagonal.isEmpty()) {
                    continue;
                }
                Piece piece = position.at(diagonal.get());
                boolean capture = piece != null && piece.color() != color;
                if (capture || diagonal.get().equals(position.enPassant)) {
                    targets.add(diagonal.get());
                }
            }
            return targets;
        }
    }

    private static final Map<Character, MoveRule> RULES = Map.of(
            'P', new PawnRule(),
            'N', new StepRule(KNIGHT_STEPS),
            'B', new SlideRule(DIAGONAL),
            'R', new SlideRule(ORTHOGONAL),
            'Q', new SlideRule(java.util.stream.Stream.concat(Arrays.stream(ORTHOGONAL), Arrays.stream(DIAGONAL))
                    .toArray(int[][]::new)),
            'K', new KingRule());

    private Position position;

    public ChessGame(String fen) {
        position = Position.fromFen(fen);
    }

    public String move(String source, String target) {
        Optional<Square> start = Square.parse(source);
        Optional<Square> end = Square.parse(target);
        if (start.isEmpty() || end.isEmpty() || !legalTargets(start.get()).contains(end.get())) {
            return "ILLEGAL";
        }
        position = position.play(start.get(), end.get());
        boolean inCheck = position.inCheck(position.side);
        if (!hasLegalMove()) {
            return inCheck ? "CHECKMATE" : "STALEMATE";
        }
        return inCheck ? "CHECK" : "OK";
    }

    public String pieceAt(String square) {
        return Square.parse(square).map(position::at).map(Piece::code).orElse("");
    }

    public String turn() {
        return position.side == WHITE ? "WHITE" : "BLACK";
    }

    public List<String> legalMoves(String square) {
        return Square.parse(square)
                .map(parsed -> legalTargets(parsed).stream().map(Square::name).sorted().toList())
                .orElse(List.of());
    }

    public boolean inCheck() {
        return position.inCheck(position.side);
    }

    /** Pseudo-legal targets that do not leave the mover's own king attacked. */
    private List<Square> legalTargets(Square square) {
        Piece piece = position.at(square);
        if (piece == null || piece.color() != position.side) {
            return List.of();
        }
        Position current = position;
        return RULES.get(piece.kind()).targets(current, square, piece.color()).stream()
                .filter(target -> !current.play(square, target).inCheck(piece.color()))
                .toList();
    }

    private boolean hasLegalMove() {
        for (int index = 0; index < 64; index++) {
            Square square = new Square(index % 8, index / 8);
            Piece piece = position.at(square);
            if (piece != null && piece.color() == position.side && !legalTargets(square).isEmpty()) {
                return true;
            }
        }
        return false;
    }
}
