use std::collections::HashMap;

/// A tree node. A pattern has at most 100 characters, so the tree is shallow and recursion over
/// it is safe.
enum Node {
    Lit(u8),
    Any,
    Empty,
    Class(bool, Vec<(u8, u8)>),
    Cat(Vec<Node>),
    Alt(Vec<Node>),
    Star(Box<Node>),
    Plus(Box<Node>),
    Opt(Box<Node>),
}

fn show_class(negated: bool, items: &[(u8, u8)]) -> String {
    let parts: Vec<String> = items
        .iter()
        .map(|&(low, high)| {
            if low == high {
                format!("'{}'", low as char)
            } else {
                format!("'{}'-'{}'", low as char, high as char)
            }
        })
        .collect();
    let head = if negated { "notclass(" } else { "class(" };
    format!("{}{})", head, parts.join(","))
}

fn show(node: &Node) -> String {
    let joined = |kind: &str, parts: &[Node]| {
        let shown: Vec<String> = parts.iter().map(show).collect();
        format!("{}({})", kind, shown.join(","))
    };
    match node {
        Node::Lit(c) => format!("'{}'", *c as char),
        Node::Any => "any".to_string(),
        Node::Empty => "empty".to_string(),
        Node::Class(negated, items) => show_class(*negated, items),
        Node::Cat(parts) => joined("cat", parts),
        Node::Alt(parts) => joined("alt", parts),
        Node::Star(inner) => format!("star({})", show(inner)),
        Node::Plus(inner) => format!("plus({})", show(inner)),
        Node::Opt(inner) => format!("opt({})", show(inner)),
    }
}

struct PatternError {
    code: &'static str,
    position: usize,
}

/// Recursive descent over the grammar alternation > sequence > repetition > atom.
struct Parser<'a> {
    text: &'a [u8],
    pos: usize,
}

impl<'a> Parser<'a> {
    fn peek(&self) -> Option<u8> {
        self.text.get(self.pos).copied()
    }

    fn fail<T>(code: &'static str, position: usize) -> Result<T, PatternError> {
        Err(PatternError { code, position })
    }

    fn parse(&mut self) -> Result<Node, PatternError> {
        let node = self.alternation()?;
        if self.pos < self.text.len() {
            return Self::fail("unmatched-paren", self.pos);
        }
        Ok(node)
    }

    fn alternation(&mut self) -> Result<Node, PatternError> {
        let mut branches = vec![self.sequence()?];
        while self.peek() == Some(b'|') {
            self.pos += 1;
            branches.push(self.sequence()?);
        }
        Ok(if branches.len() == 1 { branches.pop().unwrap() } else { Node::Alt(branches) })
    }

    fn sequence(&mut self) -> Result<Node, PatternError> {
        let mut items = Vec::new();
        while let Some(c) = self.peek() {
            if c == b'|' || c == b')' {
                break;
            }
            items.push(self.repetition()?);
        }
        Ok(match items.len() {
            0 => Node::Empty,
            1 => items.pop().unwrap(),
            _ => Node::Cat(items),
        })
    }

    fn repetition(&mut self) -> Result<Node, PatternError> {
        if matches!(self.peek(), Some(b'*' | b'+' | b'?')) {
            return Self::fail("nothing-to-repeat", self.pos);
        }
        let mut node = self.atom()?;
        loop {
            node = match self.peek() {
                Some(b'*') => Node::Star(Box::new(node)),
                Some(b'+') => Node::Plus(Box::new(node)),
                Some(b'?') => Node::Opt(Box::new(node)),
                _ => return Ok(node),
            };
            self.pos += 1;
        }
    }

    fn atom(&mut self) -> Result<Node, PatternError> {
        let start = self.pos;
        let c = self.text[self.pos];
        self.pos += 1;
        match c {
            b'(' => {
                let inner = self.alternation()?;
                if self.peek() != Some(b')') {
                    return Self::fail("unclosed-group", start);
                }
                self.pos += 1;
                Ok(inner)
            }
            b'.' => Ok(Node::Any),
            b'[' => self.char_class(start),
            _ => Ok(Node::Lit(c)),
        }
    }

    fn char_class(&mut self, start: usize) -> Result<Node, PatternError> {
        let negated = self.peek() == Some(b'^');
        if negated {
            self.pos += 1;
        }
        let mut items = Vec::new();
        loop {
            let c = match self.peek() {
                None => return Self::fail("unclosed-class", start),
                Some(c) => c,
            };
            if c == b']' {
                if items.is_empty() {
                    return Self::fail("empty-class", start);
                }
                self.pos += 1;
                return Ok(Node::Class(negated, items));
            }
            let low_at = self.pos;
            self.pos += 1;
            let is_range = self.peek() == Some(b'-')
                && self.pos + 1 < self.text.len()
                && self.text[self.pos + 1] != b']';
            if is_range {
                let high = self.text[self.pos + 1];
                if high < c {
                    return Self::fail("bad-range", low_at);
                }
                self.pos += 2;
                items.push((c, high));
            } else {
                items.push((c, c));
            }
        }
    }
}

#[derive(Clone, PartialEq)]
enum Kind {
    Char(u8),
    AnyChar,
    Class(bool, Vec<(u8, u8)>),
    Split,
    Empty,
    Match,
}

/// The states of the automaton: the kind of each one and its arrows.
struct Automaton {
    kind: Vec<Kind>,
    outs: Vec<Vec<usize>>,
    final_state: usize,
}

const LOOSE: usize = usize::MAX;

struct Builder {
    kind: Vec<Kind>,
    outs: Vec<Vec<usize>>,
}

impl Builder {
    fn add(&mut self, kind: Kind, arrows: usize) -> usize {
        self.kind.push(kind);
        self.outs.push(vec![LOOSE; arrows]);
        self.kind.len() - 1
    }

    fn patch(&mut self, holes: &[(usize, usize)], target: usize) {
        for &(state, index) in holes {
            self.outs[state][index] = target;
        }
    }

    fn single(&mut self, kind: Kind) -> (usize, Vec<(usize, usize)>) {
        let state = self.add(kind, 1);
        (state, vec![(state, 0)])
    }

    fn repeat(&mut self, inner: &Node, loops: bool, starts_inside: bool) -> (usize, Vec<(usize, usize)>) {
        let (start, mut holes) = self.fragment(inner);
        let split = self.add(Kind::Split, 2);
        self.outs[split][0] = start;
        if loops {
            self.patch(&holes, split);
            holes.clear();
        }
        holes.push((split, 1));
        (if starts_inside { start } else { split }, holes)
    }

    fn fragment(&mut self, node: &Node) -> (usize, Vec<(usize, usize)>) {
        match node {
            Node::Lit(c) => self.single(Kind::Char(*c)),
            Node::Any => self.single(Kind::AnyChar),
            Node::Empty => self.single(Kind::Empty),
            Node::Class(negated, items) => self.single(Kind::Class(*negated, items.clone())),
            Node::Cat(parts) => {
                let (start, mut holes) = self.fragment(&parts[0]);
                for part in &parts[1..] {
                    let (next, next_holes) = self.fragment(part);
                    self.patch(&holes, next);
                    holes = next_holes;
                }
                (start, holes)
            }
            Node::Alt(parts) => {
                let split = self.add(Kind::Split, parts.len());
                let mut holes = Vec::new();
                for (index, part) in parts.iter().enumerate() {
                    let (side, side_holes) = self.fragment(part);
                    self.outs[split][index] = side;
                    holes.extend(side_holes);
                }
                (split, holes)
            }
            Node::Star(inner) => self.repeat(inner, true, false),
            Node::Plus(inner) => self.repeat(inner, true, true),
            Node::Opt(inner) => self.repeat(inner, false, false),
        }
    }
}

impl Automaton {
    /// Builds the fragments, adds the match state and renumbers breadth first from the start
    /// state: the start is 0, and each arrow's unseen target is next.
    fn new(root: &Node) -> Self {
        let mut builder = Builder { kind: Vec::new(), outs: Vec::new() };
        let (start, holes) = builder.fragment(root);
        let match_state = builder.add(Kind::Match, 0);
        builder.patch(&holes, match_state);
        let mut number = vec![LOOSE; builder.kind.len()];
        number[start] = 0;
        let mut order = vec![start];
        let mut i = 0;
        while i < order.len() {
            for &target in &builder.outs[order[i]] {
                if number[target] == LOOSE {
                    number[target] = order.len();
                    order.push(target);
                }
            }
            i += 1;
        }
        let kind: Vec<Kind> = order.iter().map(|&s| builder.kind[s].clone()).collect();
        let outs = order
            .iter()
            .map(|&s| builder.outs[s].iter().map(|&t| number[t]).collect())
            .collect();
        let final_state = kind.iter().position(|k| *k == Kind::Match).unwrap();
        Automaton { kind, outs, final_state }
    }

    fn line(&self, state: usize) -> String {
        let head = match &self.kind[state] {
            Kind::Char(c) => format!("char '{}'", *c as char),
            Kind::AnyChar => "any".to_string(),
            Kind::Class(negated, items) => show_class(*negated, items),
            Kind::Split => "split".to_string(),
            Kind::Empty => "empty".to_string(),
            Kind::Match => "match".to_string(),
        };
        if self.outs[state].is_empty() {
            return format!("{}: {}", state, head);
        }
        let targets: Vec<String> = self.outs[state].iter().map(|t| t.to_string()).collect();
        format!("{}: {} -> {}", state, head, targets.join(", "))
    }

    fn accepts(&self, state: usize, c: u8) -> bool {
        match &self.kind[state] {
            Kind::Char(expected) => *expected == c,
            Kind::AnyChar => true,
            Kind::Class(negated, items) => {
                items.iter().any(|&(low, high)| low <= c && c <= high) != *negated
            }
            _ => false,
        }
    }

    /// Every state reachable from the sources through split and empty arrows, sources included.
    fn closure(&self, sources: &[usize]) -> Vec<usize> {
        let mut seen = vec![false; self.kind.len()];
        let mut reached = Vec::new();
        let mut stack: Vec<usize> = sources.iter().rev().copied().collect();
        while let Some(state) = stack.pop() {
            if seen[state] {
                continue;
            }
            seen[state] = true;
            reached.push(state);
            if matches!(self.kind[state], Kind::Split | Kind::Empty) {
                stack.extend(self.outs[state].iter().rev());
            }
        }
        reached
    }

    fn run(&self, text: &[u8]) -> (bool, i32) {
        let mut current = self.closure(&[0]);
        let mut steps = current.len() as i32;
        for &c in text {
            let targets: Vec<usize> = current
                .iter()
                .filter(|&&s| self.accepts(s, c))
                .map(|&s| self.outs[s][0])
                .collect();
            current = self.closure(&targets);
            steps += current.len() as i32;
            if current.is_empty() {
                return (false, steps);
            }
        }
        (current.contains(&self.final_state), steps)
    }

    /// One pass: each live state carries the earliest start that reaches it, and the live list
    /// stays ordered by start. After a match, later starts are dropped and the scan goes on while
    /// a state with that start or an earlier one is alive.
    fn leftmost_longest(&self, text: &[u8]) -> Vec<i32> {
        let mut best: Option<(usize, usize)> = None;
        let mut live: Vec<(usize, usize)> = Vec::new();
        for position in 0..=text.len() {
            if best.is_none() {
                let mut have = vec![false; self.kind.len()];
                for &(state, _) in &live {
                    have[state] = true;
                }
                for state in self.closure(&[0]) {
                    if !have[state] {
                        live.push((state, position));
                    }
                }
            }
            for &(state, start) in &live {
                if state == self.final_state && best.map_or(true, |(s, _)| start <= s) {
                    best = Some((start, position));
                }
            }
            if let Some((limit, _)) = best {
                live.retain(|&(_, start)| start <= limit);
            }
            if position == text.len() || live.is_empty() {
                break;
            }
            let mut seen = vec![false; self.kind.len()];
            let mut moved = Vec::new();
            for &(state, start) in &live {
                if !self.accepts(state, text[position]) {
                    continue;
                }
                for reached in self.closure(&[self.outs[state][0]]) {
                    if !seen[reached] {
                        seen[reached] = true;
                        moved.push((reached, start));
                    }
                }
            }
            live = moved;
        }
        match best {
            Some((start, end)) => vec![start as i32, end as i32],
            None => vec![-1, -1],
        }
    }
}

/// A recursive-descent parser builds the syntax tree; Thompson's construction turns it into an
/// automaton with one state per character, class or operator; matching runs every live state in
/// step with the text, so it never backtracks. Compiled automata are cached by pattern.
pub struct RegexEngine {
    automata: HashMap<String, Automaton>,
}

impl RegexEngine {
    pub fn new() -> Self {
        RegexEngine { automata: HashMap::new() }
    }

    fn automaton(&mut self, pattern: &str) -> &Automaton {
        self.automata.entry(pattern.to_string()).or_insert_with(|| {
            let mut parser = Parser { text: pattern.as_bytes(), pos: 0 };
            match parser.parse() {
                Ok(root) => Automaton::new(&root),
                Err(_) => panic!("an invalid pattern reached the automaton"),
            }
        })
    }

    // Level 1
    pub fn parse(&mut self, pattern: String) -> String {
        let mut parser = Parser { text: pattern.as_bytes(), pos: 0 };
        match parser.parse() {
            Ok(root) => show(&root),
            Err(error) => format!("error: {} at {}", error.code, error.position),
        }
    }

    // Level 2
    pub fn nfa(&mut self, pattern: String) -> Vec<String> {
        let automaton = self.automaton(&pattern);
        (0..automaton.kind.len()).map(|state| automaton.line(state)).collect()
    }

    // Level 3
    pub fn full_match(&mut self, pattern: String, text: String) -> bool {
        self.automaton(&pattern).run(text.as_bytes()).0
    }

    pub fn count_steps(&mut self, pattern: String, text: String) -> i32 {
        self.automaton(&pattern).run(text.as_bytes()).1
    }

    // Level 4
    pub fn search(&mut self, pattern: String, text: String) -> Vec<i32> {
        self.automaton(&pattern).leftmost_longest(text.as_bytes())
    }
}
