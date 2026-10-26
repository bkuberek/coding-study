private const val WHITE = 'w'
private const val BLACK = 'b'
private const val FILES = "abcdefgh"

private val KNIGHT_STEPS = listOf(1 to 2, 2 to 1, 2 to -1, 1 to -2, -1 to -2, -2 to -1, -2 to 1, -1 to 2)
private val KING_STEPS = listOf(1 to 0, 1 to 1, 0 to 1, -1 to 1, -1 to 0, -1 to -1, 0 to -1, 1 to -1)
private val ORTHOGONAL = listOf(1 to 0, -1 to 0, 0 to 1, 0 to -1)
private val DIAGONAL = listOf(1 to 1, 1 to -1, -1 to 1, -1 to -1)

private fun opponent(color: Char): Char = if (color == WHITE) BLACK else WHITE

private data class Square(val file: Int, val rank: Int) {
    fun offset(step: Pair<Int, Int>): Square? {
        val (files, ranks) = step
        val next = Square(file + files, rank + ranks)
        return next.takeIf { it.file in 0..7 && it.rank in 0..7 }
    }

    val name: String get() = "${FILES[file]}${rank + 1}"

    companion object {
        fun parse(text: String): Square? {
            if (text.length != 2 || text[0] !in FILES || text[1] !in '1'..'8') {
                return null
            }
            return Square(FILES.indexOf(text[0]), text[1] - '1')
        }
    }
}

private data class Piece(val color: Char, val kind: Char) {
    val code: String get() = "$color$kind"
}

private val ROOK_HOMES = mapOf(Square(0, 0) to 'Q', Square(7, 0) to 'K', Square(0, 7) to 'q', Square(7, 7) to 'k')

/** An immutable snapshot: pieces, side to move, castling rights and the en passant square. */
private class Position(
    private val cells: List<Piece?>, // index rank * 8 + file
    val side: Char,
    val castling: Set<Char>,
    val enPassant: Square?,
) {
    fun at(square: Square): Piece? = cells[square.rank * 8 + square.file]

    fun isFreeFor(square: Square, color: Char): Boolean = at(square)?.color != color

    fun squaresOf(color: Char): List<Square> =
        cells.indices.filter { cells[it]?.color == color }.map { Square(it % 8, it / 8) }

    fun inCheck(color: Char): Boolean {
        val king = cells.indexOf(Piece(color, 'K'))
        return attacked(Square(king % 8, king / 8), opponent(color))
    }

    /** Whether any piece of [by] attacks [square] (pawns by their capture direction). */
    fun attacked(square: Square, by: Char): Boolean {
        val forward = if (by == WHITE) 1 else -1
        val byPawn = listOf(-1, 1).any { files -> square.offset(files to -forward)?.let(::at) == Piece(by, 'P') }
        val byKnight = KNIGHT_STEPS.any { square.offset(it)?.let(::at) == Piece(by, 'N') }
        val byKing = KING_STEPS.any { square.offset(it)?.let(::at) == Piece(by, 'K') }
        val byLine = ORTHOGONAL.any { firstPiece(square, it).isOneOf(by, "RQ") } ||
            DIAGONAL.any { firstPiece(square, it).isOneOf(by, "BQ") }
        return byPawn || byKnight || byKing || byLine
    }

    private fun Piece?.isOneOf(color: Char, kinds: String): Boolean = this != null && this.color == color && kind in kinds

    /** Squares along [direction] up to and including the first occupied one. */
    fun ray(start: Square, direction: Pair<Int, Int>): List<Square> {
        val squares = mutableListOf<Square>()
        var next = start.offset(direction)
        while (next != null) {
            squares += next
            if (at(next) != null) {
                break
            }
            next = next.offset(direction)
        }
        return squares
    }

    private fun firstPiece(start: Square, direction: Pair<Int, Int>): Piece? = ray(start, direction).lastOrNull()?.let(::at)

    /** The position after moving the piece on [source] to [target] (assumed pseudo-legal). */
    fun play(source: Square, target: Square): Position {
        val piece = at(source) ?: return this
        val next = cells.toMutableList()
        val rank = source.rank
        next[rank * 8 + source.file] = null
        if (piece.kind == 'P' && target == enPassant) {
            next[rank * 8 + target.file] = null // the pawn captured en passant
        }
        if (piece.kind == 'K' && kotlin.math.abs(target.file - source.file) == 2) {
            val (rookFrom, rookTo) = if (target.file == 6) 7 to 5 else 0 to 3
            next[rank * 8 + rookTo] = next[rank * 8 + rookFrom]
            next[rank * 8 + rookFrom] = null
        }
        val lastRank = if (piece.color == WHITE) 7 else 0
        val promoted = piece.kind == 'P' && target.rank == lastRank
        next[target.rank * 8 + target.file] = if (promoted) Piece(piece.color, 'Q') else piece
        val lost = listOfNotNull(ROOK_HOMES[source], ROOK_HOMES[target]).toMutableSet()
        if (piece.kind == 'K') {
            lost += if (piece.color == WHITE) setOf('K', 'Q') else setOf('k', 'q')
        }
        val doublePush = piece.kind == 'P' && kotlin.math.abs(target.rank - rank) == 2
        val passed = if (doublePush) Square(source.file, (rank + target.rank) / 2) else null
        return Position(next, opponent(side), castling - lost, passed)
    }

    companion object {
        fun fromFen(fen: String): Position {
            val (placement, side, castling, enPassant) = fen.split(" ")
            val cells = MutableList<Piece?>(64) { null }
            placement.split("/").forEachIndexed { row, text ->
                var file = 0
                for (symbol in text) {
                    if (symbol.isDigit()) {
                        file += symbol.digitToInt()
                        continue
                    }
                    val color = if (symbol.isUpperCase()) WHITE else BLACK
                    cells[(7 - row) * 8 + file] = Piece(color, symbol.uppercaseChar())
                    file++
                }
            }
            val rights = if (castling == "-") emptySet() else castling.toSet()
            return Position(cells, side[0], rights, Square.parse(enPassant))
        }
    }
}

private fun interface MoveRule {
    fun targets(position: Position, square: Square, color: Char): List<Square>
}

private open class StepRule(private val steps: List<Pair<Int, Int>>) : MoveRule {
    override fun targets(position: Position, square: Square, color: Char): List<Square> =
        steps.mapNotNull { square.offset(it) }.filter { position.isFreeFor(it, color) }
}

private class SlideRule(private val rays: List<Pair<Int, Int>>) : MoveRule {
    override fun targets(position: Position, square: Square, color: Char): List<Square> =
        rays.flatMap { ray -> position.ray(square, ray).filter { position.isFreeFor(it, color) } }
}

private class KingRule : StepRule(KING_STEPS) {
    override fun targets(position: Position, square: Square, color: Char): List<Square> =
        super.targets(position, square, color) + castling(position, square, color)

    private fun castling(position: Position, square: Square, color: Char): List<Square> {
        val rank = if (color == WHITE) 0 else 7
        if (square != Square(4, rank) || position.attacked(square, opponent(color))) {
            return emptyList()
        }
        data class Side(val right: Char, val rookFile: Int, val empty: List<Int>, val crossed: List<Int>)
        val sides = listOf(Side('K', 7, listOf(5, 6), listOf(5, 6)), Side('Q', 0, listOf(1, 2, 3), listOf(3, 2)))
        return sides.filter { side ->
            val letter = if (color == WHITE) side.right else side.right.lowercaseChar()
            letter in position.castling &&
                position.at(Square(side.rookFile, rank)) == Piece(color, 'R') &&
                side.empty.all { position.at(Square(it, rank)) == null } &&
                side.crossed.none { position.attacked(Square(it, rank), opponent(color)) }
        }.map { Square(it.crossed.last(), rank) }
    }
}

private class PawnRule : MoveRule {
    override fun targets(position: Position, square: Square, color: Char): List<Square> {
        val forward = if (color == WHITE) 1 else -1
        val startRank = if (color == WHITE) 1 else 6
        val targets = mutableListOf<Square>()
        val one = square.offset(0 to forward)
        if (one != null && position.at(one) == null) {
            targets += one
            val two = square.offset(0 to 2 * forward)
            if (square.rank == startRank && two != null && position.at(two) == null) {
                targets += two
            }
        }
        for (files in listOf(-1, 1)) {
            val diagonal = square.offset(files to forward) ?: continue
            val piece = position.at(diagonal)
            if ((piece != null && piece.color != color) || diagonal == position.enPassant) {
                targets += diagonal
            }
        }
        return targets
    }
}

private val RULES: Map<Char, MoveRule> = mapOf(
    'P' to PawnRule(),
    'N' to StepRule(KNIGHT_STEPS),
    'B' to SlideRule(DIAGONAL),
    'R' to SlideRule(ORTHOGONAL),
    'Q' to SlideRule(ORTHOGONAL + DIAGONAL),
    'K' to KingRule(),
)

class ChessGame(fen: String) {
    private var position = Position.fromFen(fen)

    fun move(source: String, target: String): String {
        val start = Square.parse(source) ?: return "ILLEGAL"
        val end = Square.parse(target) ?: return "ILLEGAL"
        if (end !in legalTargets(start)) {
            return "ILLEGAL"
        }
        position = position.play(start, end)
        val inCheck = position.inCheck(position.side)
        if (!hasLegalMove()) {
            return if (inCheck) "CHECKMATE" else "STALEMATE"
        }
        return if (inCheck) "CHECK" else "OK"
    }

    fun pieceAt(square: String): String = Square.parse(square)?.let(position::at)?.code ?: ""

    fun turn(): String = if (position.side == WHITE) "WHITE" else "BLACK"

    fun legalMoves(square: String): List<String> =
        Square.parse(square)?.let { parsed -> legalTargets(parsed).map { it.name }.sorted() }.orEmpty()

    fun inCheck(): Boolean = position.inCheck(position.side)

    /** Pseudo-legal targets that do not leave the mover's own king attacked. */
    private fun legalTargets(square: Square): List<Square> {
        val current = position
        val piece = current.at(square)?.takeIf { it.color == current.side } ?: return emptyList()
        return RULES.getValue(piece.kind).targets(current, square, piece.color)
            .filter { !current.play(square, it).inCheck(piece.color) }
    }

    private fun hasLegalMove(): Boolean = position.squaresOf(position.side).any { legalTargets(it).isNotEmpty() }
}
