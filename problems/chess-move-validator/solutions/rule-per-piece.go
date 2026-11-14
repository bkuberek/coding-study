package chess_move_validator

import (
	"slices"
	"sort"
	"strings"
	"unicode"
)

type color byte

const (
	white color = 'w'
	black color = 'b'
)

func (c color) opponent() color {
	if c == white {
		return black
	}
	return white
}

type step [2]int

var (
	knightSteps = []step{{1, 2}, {2, 1}, {2, -1}, {1, -2}, {-1, -2}, {-2, -1}, {-2, 1}, {-1, 2}}
	kingSteps   = []step{{1, 0}, {1, 1}, {0, 1}, {-1, 1}, {-1, 0}, {-1, -1}, {0, -1}, {1, -1}}
	orthogonal  = []step{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}
	diagonal    = []step{{1, 1}, {1, -1}, {-1, 1}, {-1, -1}}
)

const fileNames = "abcdefgh"

type square struct {
	file, rank int
}

func parseSquare(text string) (square, bool) {
	if len(text) != 2 || !strings.ContainsRune(fileNames, rune(text[0])) || text[1] < '1' || text[1] > '8' {
		return square{}, false
	}
	return square{int(text[0] - 'a'), int(text[1] - '1')}, true
}

// offset returns the square files and ranks away, or false when it falls off the board.
func (s square) offset(st step) (square, bool) {
	file, rank := s.file+st[0], s.rank+st[1]
	if file < 0 || file >= 8 || rank < 0 || rank >= 8 {
		return square{}, false
	}
	return square{file, rank}, true
}

func (s square) name() string {
	return string(fileNames[s.file]) + string(rune('1'+s.rank))
}

// piece is a color and a kind (P, N, B, R, Q or K); the zero value is an empty square.
type piece struct {
	color color
	kind  byte
}

func (p piece) code() string {
	return string(rune(p.color)) + string(rune(p.kind))
}

type rights uint8

const (
	whiteKingside rights = 1 << iota
	whiteQueenside
	blackKingside
	blackQueenside
)

// rookHomes maps the corner squares to the castling right that depends on the rook there.
var rookHomes = map[square]rights{
	{0, 0}: whiteQueenside,
	{7, 0}: whiteKingside,
	{0, 7}: blackQueenside,
	{7, 7}: blackKingside,
}

// position is an immutable snapshot: pieces, side to move, castling rights and the en passant
// square. Methods that change it return a new value.
type position struct {
	cells        [64]piece // index rank*8 + file
	side         color
	castling     rights
	enPassant    square
	hasEnPassant bool
}

func fromFEN(fen string) position {
	fields := strings.Fields(fen)
	var p position
	for row, text := range strings.Split(fields[0], "/") {
		file := 0
		for _, char := range text {
			if unicode.IsDigit(char) {
				file += int(char - '0')
				continue
			}
			c := black
			if unicode.IsUpper(char) {
				c = white
			}
			p.cells[(7-row)*8+file] = piece{c, byte(unicode.ToUpper(char))}
			file++
		}
	}
	p.side = color(fields[1][0])
	for _, char := range fields[2] {
		switch char {
		case 'K':
			p.castling |= whiteKingside
		case 'Q':
			p.castling |= whiteQueenside
		case 'k':
			p.castling |= blackKingside
		case 'q':
			p.castling |= blackQueenside
		}
	}
	p.enPassant, p.hasEnPassant = parseSquare(fields[3])
	return p
}

func (p *position) at(s square) piece {
	return p.cells[s.rank*8+s.file]
}

func (p *position) isEnemy(s square, c color) bool {
	other := p.at(s)
	return other != piece{} && other.color != c
}

func (p *position) isEnPassant(s square) bool {
	return p.hasEnPassant && s == p.enPassant
}

func (p *position) king(c color) square {
	for index, cell := range p.cells {
		if cell == (piece{c, 'K'}) {
			return square{index % 8, index / 8}
		}
	}
	return square{}
}

func (p *position) inCheck(c color) bool {
	return p.attacked(p.king(c), c.opponent())
}

// attacked reports whether any piece of by attacks s (pawns by their capture direction).
func (p *position) attacked(s square, by color) bool {
	forward := 1
	if by == black {
		forward = -1
	}
	for _, files := range []int{-1, 1} {
		if origin, ok := s.offset(step{files, -forward}); ok && p.at(origin) == (piece{by, 'P'}) {
			return true
		}
	}
	for _, leaper := range []struct {
		kind  byte
		steps []step
	}{{'N', knightSteps}, {'K', kingSteps}} {
		for _, st := range leaper.steps {
			if origin, ok := s.offset(st); ok && p.at(origin) == (piece{by, leaper.kind}) {
				return true
			}
		}
	}
	for _, slider := range []struct {
		kinds string
		rays  []step
	}{{"RQ", orthogonal}, {"BQ", diagonal}} {
		for _, ray := range slider.rays {
			if found := p.firstPiece(s, ray); found.color == by && strings.IndexByte(slider.kinds, found.kind) >= 0 {
				return true
			}
		}
	}
	return false
}

// firstPiece returns the first piece along direction, or the empty piece.
func (p *position) firstPiece(start square, direction step) piece {
	for _, s := range p.ray(start, direction) {
		if found := p.at(s); found != (piece{}) {
			return found
		}
	}
	return piece{}
}

// ray returns the squares along direction up to and including the first occupied one.
func (p *position) ray(start square, direction step) []square {
	var squares []square
	for s, ok := start.offset(direction); ok; s, ok = s.offset(direction) {
		squares = append(squares, s)
		if p.at(s) != (piece{}) {
			break
		}
	}
	return squares
}

// play returns the position after moving the piece on source to target (assumed pseudo-legal).
func (p *position) play(source, target square) position {
	moving := p.at(source)
	next := *p
	next.cells[source.rank*8+source.file] = piece{}
	if moving.kind == 'P' && p.isEnPassant(target) {
		next.cells[source.rank*8+target.file] = piece{} // the pawn captured en passant
	}
	if moving.kind == 'K' && abs(target.file-source.file) == 2 {
		rookFrom, rookTo := 0, 3
		if target.file == 6 {
			rookFrom, rookTo = 7, 5
		}
		next.cells[source.rank*8+rookTo] = next.cells[source.rank*8+rookFrom]
		next.cells[source.rank*8+rookFrom] = piece{}
	}
	lastRank := 0
	if moving.color == white {
		lastRank = 7
	}
	placed := moving
	if moving.kind == 'P' && target.rank == lastRank {
		placed = piece{moving.color, 'Q'}
	}
	next.cells[target.rank*8+target.file] = placed
	next.side = p.side.opponent()
	next.castling = p.castling &^ rightsLost(moving, source, target)
	next.enPassant, next.hasEnPassant = square{}, false
	if moving.kind == 'P' && abs(target.rank-source.rank) == 2 {
		next.enPassant, next.hasEnPassant = square{source.file, (source.rank + target.rank) / 2}, true
	}
	return next
}

func rightsLost(moving piece, source, target square) rights {
	lost := rookHomes[source] | rookHomes[target]
	if moving.kind == 'K' {
		if moving.color == white {
			lost |= whiteKingside | whiteQueenside
		} else {
			lost |= blackKingside | blackQueenside
		}
	}
	return lost
}

func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}

// moveRule lists the pseudo-legal targets of one kind of piece: where it can go, without regard
// to leaving its own king attacked.
type moveRule interface {
	targets(p *position, from square, c color) []square
}

type stepRule struct {
	steps []step
}

func (r stepRule) targets(p *position, from square, c color) []square {
	var result []square
	for _, st := range r.steps {
		if target, ok := from.offset(st); ok && (p.at(target) == piece{} || p.isEnemy(target, c)) {
			result = append(result, target)
		}
	}
	return result
}

type slideRule struct {
	rays []step
}

func (r slideRule) targets(p *position, from square, c color) []square {
	var result []square
	for _, ray := range r.rays {
		for _, target := range p.ray(from, ray) {
			if p.at(target) == (piece{}) || p.isEnemy(target, c) {
				result = append(result, target)
			}
		}
	}
	return result
}

// kingRule is the step rule plus castling.
type kingRule struct {
	stepRule
}

type castlingSide struct {
	white, black rights
	rookFile     int
	empty        []int // files that must be empty
	crossed      []int // files the king crosses or lands on, the last being its destination
}

var castlingSides = []castlingSide{
	{whiteKingside, blackKingside, 7, []int{5, 6}, []int{5, 6}},
	{whiteQueenside, blackQueenside, 0, []int{1, 2, 3}, []int{3, 2}},
}

func (r kingRule) targets(p *position, from square, c color) []square {
	return append(r.stepRule.targets(p, from, c), castlingTargets(p, from, c)...)
}

func castlingTargets(p *position, from square, c color) []square {
	rank := 0
	if c == black {
		rank = 7
	}
	if from != (square{4, rank}) || p.attacked(from, c.opponent()) {
		return nil
	}
	var result []square
sides:
	for _, side := range castlingSides {
		right := side.white
		if c == black {
			right = side.black
		}
		if p.castling&right == 0 || p.at(square{side.rookFile, rank}) != (piece{c, 'R'}) {
			continue
		}
		for _, file := range side.empty {
			if p.at(square{file, rank}) != (piece{}) {
				continue sides
			}
		}
		for _, file := range side.crossed {
			if p.attacked(square{file, rank}, c.opponent()) {
				continue sides
			}
		}
		result = append(result, square{side.crossed[len(side.crossed)-1], rank})
	}
	return result
}

type pawnRule struct{}

func (pawnRule) targets(p *position, from square, c color) []square {
	forward, startRank := 1, 1
	if c == black {
		forward, startRank = -1, 6
	}
	var result []square
	if one, ok := from.offset(step{0, forward}); ok && p.at(one) == (piece{}) {
		result = append(result, one)
		if two, ok := from.offset(step{0, 2 * forward}); ok && from.rank == startRank && p.at(two) == (piece{}) {
			result = append(result, two)
		}
	}
	for _, files := range []int{-1, 1} {
		if target, ok := from.offset(step{files, forward}); ok && (p.isEnemy(target, c) || p.isEnPassant(target)) {
			result = append(result, target)
		}
	}
	return result
}

var rules = map[byte]moveRule{
	'P': pawnRule{},
	'N': stepRule{knightSteps},
	'B': slideRule{diagonal},
	'R': slideRule{orthogonal},
	'Q': slideRule{append(append([]step{}, orthogonal...), diagonal...)},
	'K': kingRule{stepRule{kingSteps}},
}

type ChessGame struct {
	position position
}

func NewChessGame(fen string) *ChessGame {
	return &ChessGame{position: fromFEN(fen)}
}

func (g *ChessGame) Move(source string, target string) string {
	start, startOK := parseSquare(source)
	end, endOK := parseSquare(target)
	if !startOK || !endOK || !slices.Contains(g.legalTargets(start), end) {
		return "ILLEGAL"
	}
	g.position = g.position.play(start, end)
	inCheck := g.position.inCheck(g.position.side)
	if !g.hasLegalMove() {
		if inCheck {
			return "CHECKMATE"
		}
		return "STALEMATE"
	}
	if inCheck {
		return "CHECK"
	}
	return "OK"
}

func (g *ChessGame) PieceAt(square string) string {
	parsed, ok := parseSquare(square)
	if !ok {
		return ""
	}
	found := g.position.at(parsed)
	if found == (piece{}) {
		return ""
	}
	return found.code()
}

func (g *ChessGame) Turn() string {
	if g.position.side == white {
		return "WHITE"
	}
	return "BLACK"
}

func (g *ChessGame) LegalMoves(square string) []string {
	parsed, ok := parseSquare(square)
	if !ok {
		return []string{}
	}
	names := []string{}
	for _, target := range g.legalTargets(parsed) {
		names = append(names, target.name())
	}
	sort.Strings(names)
	return names
}

func (g *ChessGame) InCheck() bool {
	return g.position.inCheck(g.position.side)
}

// legalTargets returns the pseudo-legal targets that do not leave the mover's own king attacked.
func (g *ChessGame) legalTargets(from square) []square {
	p := &g.position
	mover := p.at(from)
	if mover == (piece{}) || mover.color != p.side {
		return nil
	}
	var legal []square
	for _, target := range rules[mover.kind].targets(p, from, mover.color) {
		after := p.play(from, target)
		if !after.inCheck(mover.color) {
			legal = append(legal, target)
		}
	}
	return legal
}

func (g *ChessGame) hasLegalMove() bool {
	for index, cell := range g.position.cells {
		if cell != (piece{}) && cell.color == g.position.side {
			if len(g.legalTargets(square{index % 8, index / 8})) > 0 {
				return true
			}
		}
	}
	return false
}
