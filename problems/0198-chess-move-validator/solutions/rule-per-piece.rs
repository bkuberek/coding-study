const KNIGHT_STEPS: [(i32, i32); 8] = [
    (1, 2),
    (2, 1),
    (2, -1),
    (1, -2),
    (-1, -2),
    (-2, -1),
    (-2, 1),
    (-1, 2),
];
const KING_STEPS: [(i32, i32); 8] = [
    (1, 0),
    (1, 1),
    (0, 1),
    (-1, 1),
    (-1, 0),
    (-1, -1),
    (0, -1),
    (1, -1),
];
const ORTHOGONAL: [(i32, i32); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];
const DIAGONAL: [(i32, i32); 4] = [(1, 1), (1, -1), (-1, 1), (-1, -1)];
const ALL_DIRECTIONS: [(i32, i32); 8] = [
    (1, 0),
    (-1, 0),
    (0, 1),
    (0, -1),
    (1, 1),
    (1, -1),
    (-1, 1),
    (-1, -1),
];

#[derive(Clone, Copy, PartialEq, Eq)]
enum Color {
    White,
    Black,
}

impl Color {
    fn opponent(self) -> Color {
        match self {
            Color::White => Color::Black,
            Color::Black => Color::White,
        }
    }

    fn letter(self) -> char {
        match self {
            Color::White => 'w',
            Color::Black => 'b',
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum Kind {
    Pawn,
    Knight,
    Bishop,
    Rook,
    Queen,
    King,
}

impl Kind {
    fn from_letter(letter: char) -> Option<Kind> {
        match letter.to_ascii_uppercase() {
            'P' => Some(Kind::Pawn),
            'N' => Some(Kind::Knight),
            'B' => Some(Kind::Bishop),
            'R' => Some(Kind::Rook),
            'Q' => Some(Kind::Queen),
            'K' => Some(Kind::King),
            _ => None,
        }
    }

    fn letter(self) -> char {
        match self {
            Kind::Pawn => 'P',
            Kind::Knight => 'N',
            Kind::Bishop => 'B',
            Kind::Rook => 'R',
            Kind::Queen => 'Q',
            Kind::King => 'K',
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq)]
struct Square {
    file: i32,
    rank: i32,
}

impl Square {
    fn parse(text: &str) -> Option<Square> {
        match text.as_bytes() {
            &[file @ b'a'..=b'h', rank @ b'1'..=b'8'] => Some(Square {
                file: i32::from(file - b'a'),
                rank: i32::from(rank - b'1'),
            }),
            _ => None,
        }
    }

    /// The square `files` and `ranks` away, or `None` when it falls off the board.
    fn offset(self, (files, ranks): (i32, i32)) -> Option<Square> {
        let (file, rank) = (self.file + files, self.rank + ranks);
        ((0..8).contains(&file) && (0..8).contains(&rank)).then_some(Square { file, rank })
    }

    fn index(self) -> usize {
        (self.rank * 8 + self.file) as usize
    }

    fn from_index(index: usize) -> Square {
        Square {
            file: (index % 8) as i32,
            rank: (index / 8) as i32,
        }
    }

    fn name(self) -> String {
        format!("{}{}", (b'a' + self.file as u8) as char, self.rank + 1)
    }
}

#[derive(Clone, Copy, PartialEq, Eq)]
struct Piece {
    color: Color,
    kind: Kind,
}

const WHITE_KINGSIDE: u8 = 1;
const WHITE_QUEENSIDE: u8 = 2;
const BLACK_KINGSIDE: u8 = 4;
const BLACK_QUEENSIDE: u8 = 8;

/// The castling right that depends on the rook in a corner square.
fn rook_home(square: Square) -> u8 {
    match (square.file, square.rank) {
        (0, 0) => WHITE_QUEENSIDE,
        (7, 0) => WHITE_KINGSIDE,
        (0, 7) => BLACK_QUEENSIDE,
        (7, 7) => BLACK_KINGSIDE,
        _ => 0,
    }
}

/// An immutable snapshot: pieces, side to move, castling rights and the en passant square.
/// `play` returns the next position and leaves this one untouched.
#[derive(Clone, Copy)]
struct Position {
    /// Index `rank * 8 + file`.
    cells: [Option<Piece>; 64],
    side: Color,
    castling: u8,
    en_passant: Option<Square>,
}

impl Position {
    fn from_fen(fen: &str) -> Position {
        let mut fields = fen.split_whitespace();
        let placement = fields.next().unwrap_or("");
        let side = match fields.next() {
            Some("b") => Color::Black,
            _ => Color::White,
        };
        let mut castling = 0;
        for letter in fields.next().unwrap_or("-").chars() {
            castling |= match letter {
                'K' => WHITE_KINGSIDE,
                'Q' => WHITE_QUEENSIDE,
                'k' => BLACK_KINGSIDE,
                'q' => BLACK_QUEENSIDE,
                _ => 0,
            };
        }
        let en_passant = fields.next().and_then(Square::parse);
        let mut cells = [None; 64];
        for (row, text) in placement.split('/').enumerate() {
            let mut file = 0;
            for letter in text.chars() {
                if let Some(empty) = letter.to_digit(10) {
                    file += empty as usize;
                    continue;
                }
                let color = if letter.is_ascii_uppercase() {
                    Color::White
                } else {
                    Color::Black
                };
                if let Some(kind) = Kind::from_letter(letter) {
                    cells[(7 - row) * 8 + file] = Some(Piece { color, kind });
                }
                file += 1;
            }
        }
        Position {
            cells,
            side,
            castling,
            en_passant,
        }
    }

    fn at(&self, square: Square) -> Option<Piece> {
        self.cells[square.index()]
    }

    fn is_enemy(&self, square: Square, color: Color) -> bool {
        self.at(square).is_some_and(|piece| piece.color != color)
    }

    fn king(&self, color: Color) -> Square {
        let king = Some(Piece {
            color,
            kind: Kind::King,
        });
        let index = self.cells.iter().position(|cell| *cell == king);
        Square::from_index(index.unwrap_or(0))
    }

    fn in_check(&self, color: Color) -> bool {
        self.attacked(self.king(color), color.opponent())
    }

    /// Whether any piece of `by` attacks `square` (pawns by their capture direction).
    fn attacked(&self, square: Square, by: Color) -> bool {
        let holds = |origin: Option<Square>, kind: Kind| {
            origin.is_some_and(|origin| self.at(origin) == Some(Piece { color: by, kind }))
        };
        let forward = if by == Color::White { 1 } else { -1 };
        for files in [-1, 1] {
            if holds(square.offset((files, -forward)), Kind::Pawn) {
                return true;
            }
        }
        for (kind, steps) in [(Kind::Knight, KNIGHT_STEPS), (Kind::King, KING_STEPS)] {
            if steps.iter().any(|&step| holds(square.offset(step), kind)) {
                return true;
            }
        }
        for (kind, rays) in [(Kind::Rook, ORTHOGONAL), (Kind::Bishop, DIAGONAL)] {
            for ray in rays {
                let found = self.first_piece(square, ray);
                let slides = |piece: Piece| piece.kind == kind || piece.kind == Kind::Queen;
                if found.is_some_and(|piece| piece.color == by && slides(piece)) {
                    return true;
                }
            }
        }
        false
    }

    fn first_piece(&self, start: Square, direction: (i32, i32)) -> Option<Piece> {
        self.ray(start, direction)
            .into_iter()
            .find_map(|square| self.at(square))
    }

    /// The squares along `direction` up to and including the first occupied one.
    fn ray(&self, start: Square, direction: (i32, i32)) -> Vec<Square> {
        let mut squares = Vec::new();
        let mut next = start.offset(direction);
        while let Some(square) = next {
            squares.push(square);
            if self.at(square).is_some() {
                break;
            }
            next = square.offset(direction);
        }
        squares
    }

    /// The position after moving the piece on `source` to `target` (assumed pseudo-legal).
    fn play(&self, source: Square, target: Square) -> Position {
        let mut next = *self;
        let Some(moving) = self.at(source) else {
            return next;
        };
        next.cells[source.index()] = None;
        if moving.kind == Kind::Pawn && self.en_passant == Some(target) {
            // The pawn captured en passant stands beside the source.
            next.cells[Square {
                file: target.file,
                rank: source.rank,
            }
            .index()] = None;
        }
        if moving.kind == Kind::King && (target.file - source.file).abs() == 2 {
            let (rook_from, rook_to) = if target.file == 6 { (7, 5) } else { (0, 3) };
            let row = source.rank * 8;
            next.cells[(row + rook_to) as usize] = next.cells[(row + rook_from) as usize];
            next.cells[(row + rook_from) as usize] = None;
        }
        let last_rank = if moving.color == Color::White { 7 } else { 0 };
        let promoted = moving.kind == Kind::Pawn && target.rank == last_rank;
        next.cells[target.index()] = Some(if promoted {
            Piece {
                color: moving.color,
                kind: Kind::Queen,
            }
        } else {
            moving
        });
        next.side = self.side.opponent();
        next.castling = self.castling & !rights_lost(moving, source, target);
        next.en_passant = None;
        if moving.kind == Kind::Pawn && (target.rank - source.rank).abs() == 2 {
            next.en_passant = Some(Square {
                file: source.file,
                rank: (source.rank + target.rank) / 2,
            });
        }
        next
    }
}

fn rights_lost(moving: Piece, source: Square, target: Square) -> u8 {
    let mut lost = rook_home(source) | rook_home(target);
    if moving.kind == Kind::King {
        lost |= if moving.color == Color::White {
            WHITE_KINGSIDE | WHITE_QUEENSIDE
        } else {
            BLACK_KINGSIDE | BLACK_QUEENSIDE
        };
    }
    lost
}

/// One kind of piece's pseudo-legal targets: where it can go, without regard to leaving its own
/// king attacked.
trait MoveRule {
    fn targets(&self, position: &Position, square: Square, color: Color) -> Vec<Square>;
}

struct StepRule {
    steps: &'static [(i32, i32)],
}

impl MoveRule for StepRule {
    fn targets(&self, position: &Position, square: Square, color: Color) -> Vec<Square> {
        self.steps
            .iter()
            .filter_map(|&step| square.offset(step))
            .filter(|&target| position.at(target).is_none() || position.is_enemy(target, color))
            .collect()
    }
}

struct SlideRule {
    rays: &'static [(i32, i32)],
}

impl MoveRule for SlideRule {
    fn targets(&self, position: &Position, square: Square, color: Color) -> Vec<Square> {
        self.rays
            .iter()
            .flat_map(|&ray| position.ray(square, ray))
            .filter(|&target| position.at(target).is_none() || position.is_enemy(target, color))
            .collect()
    }
}

/// The king's step rule plus castling.
struct KingRule;

/// A castling side: the right for each color, the rook's file, the files that must be empty and
/// the files the king crosses or lands on (the last one is its destination).
struct CastlingSide {
    white: u8,
    black: u8,
    rook_file: i32,
    empty: &'static [i32],
    crossed: &'static [i32],
}

const CASTLING_SIDES: [CastlingSide; 2] = [
    CastlingSide {
        white: WHITE_KINGSIDE,
        black: BLACK_KINGSIDE,
        rook_file: 7,
        empty: &[5, 6],
        crossed: &[5, 6],
    },
    CastlingSide {
        white: WHITE_QUEENSIDE,
        black: BLACK_QUEENSIDE,
        rook_file: 0,
        empty: &[1, 2, 3],
        crossed: &[3, 2],
    },
];

impl KingRule {
    fn castling(position: &Position, square: Square, color: Color) -> Vec<Square> {
        let rank = if color == Color::White { 0 } else { 7 };
        if square != (Square { file: 4, rank }) || position.attacked(square, color.opponent()) {
            return Vec::new();
        }
        let at = |file: i32| Square { file, rank };
        let rook = Some(Piece {
            color,
            kind: Kind::Rook,
        });
        let mut targets = Vec::new();
        for side in &CASTLING_SIDES {
            let right = if color == Color::White {
                side.white
            } else {
                side.black
            };
            let ready = position.castling & right != 0 && position.at(at(side.rook_file)) == rook;
            let clear = side
                .empty
                .iter()
                .all(|&file| position.at(at(file)).is_none());
            let safe = side
                .crossed
                .iter()
                .all(|&file| !position.attacked(at(file), color.opponent()));
            if ready && clear && safe {
                targets.extend(side.crossed.last().map(|&file| at(file)));
            }
        }
        targets
    }
}

impl MoveRule for KingRule {
    fn targets(&self, position: &Position, square: Square, color: Color) -> Vec<Square> {
        let steps = StepRule { steps: &KING_STEPS };
        let mut targets = steps.targets(position, square, color);
        targets.extend(KingRule::castling(position, square, color));
        targets
    }
}

struct PawnRule;

impl MoveRule for PawnRule {
    fn targets(&self, position: &Position, square: Square, color: Color) -> Vec<Square> {
        let (forward, start_rank) = if color == Color::White {
            (1, 1)
        } else {
            (-1, 6)
        };
        let mut targets = Vec::new();
        if let Some(one) = square
            .offset((0, forward))
            .filter(|&one| position.at(one).is_none())
        {
            targets.push(one);
            let two = square.offset((0, 2 * forward));
            if let Some(two) =
                two.filter(|&two| square.rank == start_rank && position.at(two).is_none())
            {
                targets.push(two);
            }
        }
        for files in [-1, 1] {
            if let Some(target) = square.offset((files, forward)) {
                if position.is_enemy(target, color) || position.en_passant == Some(target) {
                    targets.push(target);
                }
            }
        }
        targets
    }
}

fn rule_for(kind: Kind) -> &'static dyn MoveRule {
    static KNIGHT: StepRule = StepRule {
        steps: &KNIGHT_STEPS,
    };
    static BISHOP: SlideRule = SlideRule { rays: &DIAGONAL };
    static ROOK: SlideRule = SlideRule { rays: &ORTHOGONAL };
    static QUEEN: SlideRule = SlideRule {
        rays: &ALL_DIRECTIONS,
    };
    match kind {
        Kind::Pawn => &PawnRule,
        Kind::Knight => &KNIGHT,
        Kind::Bishop => &BISHOP,
        Kind::Rook => &ROOK,
        Kind::Queen => &QUEEN,
        Kind::King => &KingRule,
    }
}

pub struct ChessGame {
    position: Position,
}

impl ChessGame {
    pub fn new(fen: String) -> Self {
        ChessGame {
            position: Position::from_fen(&fen),
        }
    }

    pub fn r#move(&mut self, source: String, target: String) -> String {
        let (Some(start), Some(end)) = (Square::parse(&source), Square::parse(&target)) else {
            return "ILLEGAL".to_string();
        };
        if !self.legal_targets(start).contains(&end) {
            return "ILLEGAL".to_string();
        }
        self.position = self.position.play(start, end);
        let in_check = self.position.in_check(self.position.side);
        let verdict = if !self.has_legal_move() {
            if in_check {
                "CHECKMATE"
            } else {
                "STALEMATE"
            }
        } else if in_check {
            "CHECK"
        } else {
            "OK"
        };
        verdict.to_string()
    }

    pub fn piece_at(&mut self, square: String) -> String {
        match Square::parse(&square).and_then(|parsed| self.position.at(parsed)) {
            Some(piece) => format!("{}{}", piece.color.letter(), piece.kind.letter()),
            None => String::new(),
        }
    }

    pub fn turn(&mut self) -> String {
        match self.position.side {
            Color::White => "WHITE".to_string(),
            Color::Black => "BLACK".to_string(),
        }
    }

    pub fn legal_moves(&mut self, square: String) -> Vec<String> {
        let Some(parsed) = Square::parse(&square) else {
            return Vec::new();
        };
        let mut names: Vec<String> = self
            .legal_targets(parsed)
            .into_iter()
            .map(Square::name)
            .collect();
        names.sort();
        names
    }

    pub fn in_check(&mut self) -> bool {
        self.position.in_check(self.position.side)
    }

    /// The pseudo-legal targets that do not leave the mover's own king attacked.
    fn legal_targets(&self, square: Square) -> Vec<Square> {
        let position = &self.position;
        let Some(piece) = position
            .at(square)
            .filter(|piece| piece.color == position.side)
        else {
            return Vec::new();
        };
        rule_for(piece.kind)
            .targets(position, square, piece.color)
            .into_iter()
            .filter(|&target| !position.play(square, target).in_check(piece.color))
            .collect()
    }

    fn has_legal_move(&self) -> bool {
        self.position.cells.iter().enumerate().any(|(index, cell)| {
            cell.is_some_and(|piece| piece.color == self.position.side)
                && !self.legal_targets(Square::from_index(index)).is_empty()
        })
    }
}
