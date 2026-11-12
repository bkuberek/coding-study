use std::collections::{HashMap, HashSet, VecDeque};

enum Gen {
    Int(i32, i32),
    List(usize, usize, Box<Gen>),
    Pair(Box<Gen>, Box<Gen>),
    Filter(String, Box<Gen>),
}

#[derive(Clone)]
enum Value {
    Int(i32),
    List(Vec<Value>),
    Pair(Box<Value>, Box<Value>),
}

struct RandomStream {
    state: u32,
    discards: i32,
    limit: i32,
}

impl RandomStream {
    fn new(seed: i32, limit: i32) -> Self {
        RandomStream { state: seed as u32, discards: 0, limit }
    }

    fn next(&mut self) -> u32 {
        let mut x = self.state;
        x ^= x << 13;
        x ^= x >> 17;
        x ^= x << 5;
        self.state = x;
        x
    }

    fn between(&mut self, low: i32, high: i32) -> i32 {
        let span = (high as i64 - low as i64 + 1) as u64;
        (low as i64 + (self.next() as u64 % span) as i64) as i32
    }

    /// Counts one discarded value; `None` when the call has gone above its limit.
    fn discard(&mut self) -> Option<()> {
        self.discards += 1;
        if self.discards > self.limit { None } else { Some(()) }
    }
}

fn parse(tokens: &[&str], at: usize) -> (Gen, usize) {
    let number = |i: usize| tokens[i].parse::<i32>().unwrap();
    match tokens[at] {
        "int" => (Gen::Int(number(at + 1), number(at + 2)), at + 3),
        "list" => {
            let (element, end) = parse(tokens, at + 3);
            (Gen::List(number(at + 1) as usize, number(at + 2) as usize, Box::new(element)), end)
        }
        "pair" => {
            let (first, middle) = parse(tokens, at + 1);
            let (second, end) = parse(tokens, middle);
            (Gen::Pair(Box::new(first), Box::new(second)), end)
        }
        _ => {
            let (inner, end) = parse(tokens, at + 2);
            (Gen::Filter(tokens[at + 1].to_string(), Box::new(inner)), end)
        }
    }
}

fn generator(text: &str) -> Gen {
    let tokens: Vec<&str> = text.split(' ').collect();
    parse(&tokens, 0).0
}

/// Draws one value; `None` when the call has discarded more values than its limit allows.
fn draw(gen: &Gen, rng: &mut RandomStream) -> Option<Value> {
    match gen {
        Gen::Int(low, high) => Some(Value::Int(rng.between(*low, *high))),
        Gen::List(min, max, element) => {
            let length = rng.between(*min as i32, *max as i32);
            let mut items = Vec::new();
            for _ in 0..length {
                items.push(draw(element, rng)?);
            }
            Some(Value::List(items))
        }
        Gen::Pair(first, second) => {
            let first = draw(first, rng)?;
            let second = draw(second, rng)?;
            Some(Value::Pair(Box::new(first), Box::new(second)))
        }
        Gen::Filter(name, inner) => loop {
            let value = draw(inner, rng)?;
            if passes_filter(name, &value) {
                return Some(value);
            }
            rng.discard()?;
        },
    }
}

fn text(value: &Value) -> String {
    match value {
        Value::Int(number) => number.to_string(),
        Value::List(items) => {
            format!("[{}]", items.iter().map(text).collect::<Vec<_>>().join(","))
        }
        Value::Pair(first, second) => format!("({},{})", text(first), text(second)),
    }
}

fn number(value: &Value) -> i32 {
    match value {
        Value::Int(number) => *number,
        _ => panic!("not an integer"),
    }
}

fn items(value: &Value) -> &Vec<Value> {
    match value {
        Value::List(items) => items,
        _ => panic!("not a list"),
    }
}

fn parts(value: &Value) -> (&Value, &Value) {
    match value {
        Value::Pair(first, second) => (first, second),
        _ => panic!("not a pair"),
    }
}

fn numbers(value: &Value) -> Vec<i32> {
    items(value).iter().map(number).collect()
}

fn passes_filter(name: &str, value: &Value) -> bool {
    match name {
        "even" => number(value) % 2 == 0,
        "odd" => number(value) % 2 != 0,
        "nonzero" => number(value) != 0,
        "positive" => number(value) > 0,
        "nonempty" => !items(value).is_empty(),
        "distinct" => {
            let texts: HashSet<String> = items(value).iter().map(text).collect();
            texts.len() == items(value).len()
        }
        _ => {
            let (first, second) = parts(value);
            text(first) != text(second)
        }
    }
}

fn total(value: &Value) -> i32 {
    match value {
        Value::Int(number) => *number,
        Value::List(items) => items.iter().map(total).sum(),
        Value::Pair(first, second) => total(first) + total(second),
    }
}

fn ordered(values: &[i32]) -> bool {
    values.windows(2).all(|pair| pair[0] <= pair[1])
}

fn holds(prop: &str, value: &Value) -> bool {
    let words: Vec<&str> = prop.split(' ').collect();
    let k: i32 = if words.len() > 1 { words[1].parse().unwrap() } else { 0 };
    match words[0] {
        "lt" => number(value) < k,
        "not-multiple" => number(value) % k != 0,
        "sum-lt" => total(value) < k,
        "len-lt" => (items(value).len() as i32) < k,
        "ordered" => ordered(&numbers(value)),
        "sort-ordered" => {
            let mut list = numbers(value);
            list.sort();
            ordered(&list)
        }
        "one-pass-ordered" => {
            let mut list = numbers(value);
            for i in 0..list.len().saturating_sub(1) {
                if list[i] > list[i + 1] {
                    list.swap(i, i + 1);
                }
            }
            ordered(&list)
        }
        "max-from-zero" => {
            let list = numbers(value);
            let best = list.iter().fold(0, |best, &item| best.max(item));
            list.is_empty() || Some(&best) == list.iter().max()
        }
        "keys-distinct" => {
            let keys: HashSet<String> = items(value).iter().map(|pair| text(parts(pair).0)).collect();
            keys.len() == items(value).len()
        }
        _ => {
            let mut first: HashMap<String, String> = HashMap::new();
            let mut last: HashMap<String, String> = HashMap::new();
            for pair in items(value) {
                let (key, item) = parts(pair);
                first.entry(text(key)).or_insert_with(|| text(item));
                last.insert(text(key), text(item));
            }
            first == last
        }
    }
}

fn int_candidates(low: i32, high: i32, value: i32) -> Vec<i32> {
    let target = if low > 0 { low } else if high < 0 { high } else { 0 };
    if value == target {
        return Vec::new();
    }
    let mut found = vec![target];
    let mut step = (value - target) / 2;
    while step != 0 {
        found.push(value - step);
        step /= 2;
    }
    found
}

fn without_repeats<T>(value: &T, found: Vec<T>, show: impl Fn(&T) -> String) -> Vec<T> {
    let mut seen: HashSet<String> = HashSet::new();
    seen.insert(show(value));
    found.into_iter().filter(|candidate| seen.insert(show(candidate))).collect()
}

fn removals<T: Clone>(items: &[T], shortest: usize) -> Vec<Vec<T>> {
    let n = items.len();
    let mut found = Vec::new();
    let mut size = n;
    while size >= 1 {
        if n - size >= shortest {
            let mut start = 0;
            while start + size <= n {
                let mut shorter = items[..start].to_vec();
                shorter.extend_from_slice(&items[start + size..]);
                found.push(shorter);
                start += size;
            }
        }
        size /= 2;
    }
    found
}

fn replaced<T: Clone>(items: &[T], index: usize, item: T) -> Vec<T> {
    let mut copy = items.to_vec();
    copy[index] = item;
    copy
}

fn candidates_of(gen: &Gen, value: &Value) -> Vec<Value> {
    let mut found: Vec<Value> = Vec::new();
    match gen {
        Gen::Int(low, high) => {
            found.extend(int_candidates(*low, *high, number(value)).into_iter().map(Value::Int));
        }
        Gen::List(min, _, element) => {
            let list = items(value);
            found.extend(removals(list, *min).into_iter().map(Value::List));
            for (i, item) in list.iter().enumerate() {
                for smaller in candidates_of(element, item) {
                    found.push(Value::List(replaced(list, i, smaller)));
                }
            }
        }
        Gen::Pair(first_gen, second_gen) => {
            let (first, second) = parts(value);
            for smaller in candidates_of(first_gen, first) {
                found.push(Value::Pair(Box::new(smaller), Box::new(second.clone())));
            }
            for smaller in candidates_of(second_gen, second) {
                found.push(Value::Pair(Box::new(first.clone()), Box::new(smaller)));
            }
        }
        Gen::Filter(name, inner) => {
            found.extend(candidates_of(inner, value).into_iter().filter(|c| passes_filter(name, c)));
        }
    }
    without_repeats(value, found, text)
}

struct BoundedQueue {
    capacity: usize,
    bug: String,
    items: VecDeque<i32>,
    puts: usize,
}

impl BoundedQueue {
    fn new(capacity: i32, bug: &str) -> Self {
        BoundedQueue { capacity: capacity as usize, bug: bug.to_string(), items: VecDeque::new(), puts: 0 }
    }

    fn allows(&self, command: &str) -> bool {
        command != "get" || !self.items.is_empty()
    }

    fn apply(&mut self, command: &str) -> String {
        if command == "size" {
            let count = self.items.len();
            let shown = if self.bug == "size-wraps" { count % self.capacity } else { count };
            return shown.to_string();
        }
        if command == "get" {
            let taken = if self.bug == "wrap-lifo" && self.puts > self.capacity {
                self.items.pop_back()
            } else {
                self.items.pop_front()
            };
            return taken.map_or_else(|| "empty".to_string(), |value| value.to_string());
        }
        let value: i32 = command[4..].parse().unwrap();
        if self.items.len() == self.capacity {
            if self.bug != "full-overwrites" {
                return "full".to_string();
            }
            self.items.pop_front();
        } else if self.bug == "repeat-dropped" && self.items.back() == Some(&value) {
            self.puts += 1;
            return "ok".to_string();
        }
        self.items.push_back(value);
        self.puts += 1;
        "ok".to_string()
    }
}

fn valid(capacity: i32, commands: &[String]) -> bool {
    let mut model = BoundedQueue::new(capacity, "none");
    for command in commands {
        if !model.allows(command) {
            return false;
        }
        model.apply(command);
    }
    true
}

fn fails(capacity: i32, bug: &str, commands: &[String]) -> bool {
    let mut model = BoundedQueue::new(capacity, "none");
    let mut system = BoundedQueue::new(capacity, bug);
    commands.iter().any(|command| model.apply(command) != system.apply(command))
}

fn sequence(capacity: i32, rng: &mut RandomStream, longest: i32) -> Vec<String> {
    let mut model = BoundedQueue::new(capacity, "none");
    let length = rng.between(1, longest);
    let mut commands = Vec::new();
    for _ in 0..length {
        let allowed: &[&str] = if model.items.is_empty() { &["put", "size"] } else { &["put", "get", "size"] };
        let mut command = allowed[(rng.next() as usize) % allowed.len()].to_string();
        if command == "put" {
            command = format!("put {}", rng.between(0, 9));
        }
        model.apply(&command);
        commands.push(command);
    }
    commands
}

fn sequence_candidates(capacity: i32, commands: &[String]) -> Vec<Vec<String>> {
    let mut found = removals(commands, 1);
    for (i, command) in commands.iter().enumerate() {
        if let Some(rest) = command.strip_prefix("put ") {
            for smaller in int_candidates(0, 9, rest.parse().unwrap()) {
                found.push(replaced(commands, i, format!("put {}", smaller)));
            }
        }
    }
    let original = commands.to_vec();
    without_repeats(&original, found, |candidate| candidate.join(", "))
        .into_iter()
        .filter(|candidate| valid(capacity, candidate))
        .collect()
}

enum Outcome {
    Failed(i32, Value),
    GaveUp(i32),
    Passed,
}

/// Generators are prefix token lists parsed into a small tree. One xorshift32 stream feeds a
/// whole call, so every value is fixed by the seed and its position. Shrinking is greedy: from
/// the failing value, take the first candidate that still fails, and start again from it, until
/// no candidate fails. Candidates are built from the generator, so each one is a value the
/// generator could have drawn: in range, long enough and through every filter. The stateful
/// level runs each command sequence on the correct queue and on the buggy one and shrinks the
/// sequence the same way, keeping only sequences whose commands are all allowed.
pub struct PropertyRunner {
    limit: i32,
}

impl PropertyRunner {
    pub fn new() -> Self {
        PropertyRunner { limit: 100 }
    }

    // Level 1
    pub fn randoms(&mut self, seed: i32, count: i32) -> Vec<i64> {
        let mut rng = RandomStream::new(seed, self.limit);
        (0..count).map(|_| rng.next() as i64).collect()
    }

    pub fn generate(&mut self, gen: String, seed: i32, count: i32) -> Vec<String> {
        let mut rng = RandomStream::new(seed, self.limit);
        let parsed = generator(&gen);
        let mut values = Vec::new();
        for _ in 0..count {
            match draw(&parsed, &mut rng) {
                Some(value) => values.push(text(&value)),
                None => break,
            }
        }
        values
    }

    pub fn check(&mut self, gen: String, prop: String, seed: i32, runs: i32) -> String {
        match self.search(&gen, &prop, seed, runs) {
            Outcome::Failed(run, value) => format!("failed {}: {}", run, text(&value)),
            Outcome::GaveUp(run) => format!("gave up after {}", run),
            Outcome::Passed => format!("passed {}", runs),
        }
    }

    // Level 2
    pub fn candidates(&mut self, gen: String, seed: i32, index: i32) -> Vec<String> {
        let mut rng = RandomStream::new(seed, self.limit);
        let parsed = generator(&gen);
        let mut value = Value::Int(0);
        for _ in 0..index {
            match draw(&parsed, &mut rng) {
                Some(drawn) => value = drawn,
                None => return Vec::new(),
            }
        }
        candidates_of(&parsed, &value).iter().map(text).collect()
    }

    pub fn minimize(&mut self, gen: String, prop: String, seed: i32, runs: i32) -> Vec<String> {
        let mut value = match self.search(&gen, &prop, seed, runs) {
            Outcome::Failed(_, value) => value,
            _ => return Vec::new(),
        };
        let parsed = generator(&gen);
        let mut path = vec![text(&value)];
        while let Some(smaller) =
            candidates_of(&parsed, &value).into_iter().find(|candidate| !holds(&prop, candidate))
        {
            value = smaller;
            path.push(text(&value));
        }
        path
    }

    // Level 3
    pub fn set_discard_limit(&mut self, limit: i32) {
        self.limit = limit;
    }

    // Level 4
    pub fn replay(&mut self, capacity: i32, bug: String, commands: Vec<String>) -> Vec<String> {
        let mut model = BoundedQueue::new(capacity, "none");
        let mut system = BoundedQueue::new(capacity, &bug);
        let mut answers = Vec::new();
        for command in &commands {
            if !model.allows(command) {
                answers.push("invalid".to_string());
                break;
            }
            model.apply(command);
            answers.push(system.apply(command));
        }
        answers
    }

    pub fn generate_commands(&mut self, capacity: i32, seed: i32, count: i32, max_length: i32) -> Vec<String> {
        let mut rng = RandomStream::new(seed, self.limit);
        (0..count).map(|_| sequence(capacity, &mut rng, max_length).join(", ")).collect()
    }

    pub fn first_failure(
        &mut self,
        capacity: i32,
        bug: String,
        seed: i32,
        runs: i32,
        max_length: i32,
    ) -> Vec<String> {
        let mut rng = RandomStream::new(seed, self.limit);
        for _ in 0..runs {
            let commands = sequence(capacity, &mut rng, max_length);
            if fails(capacity, &bug, &commands) {
                return commands;
            }
        }
        Vec::new()
    }

    pub fn shrink_failure(
        &mut self,
        capacity: i32,
        bug: String,
        seed: i32,
        runs: i32,
        max_length: i32,
    ) -> Vec<String> {
        let mut commands = self.first_failure(capacity, bug.clone(), seed, runs, max_length);
        while !commands.is_empty() {
            match sequence_candidates(capacity, &commands)
                .into_iter()
                .find(|candidate| fails(capacity, &bug, candidate))
            {
                Some(smaller) => commands = smaller,
                None => break,
            }
        }
        commands
    }

    fn search(&self, gen: &str, prop: &str, seed: i32, runs: i32) -> Outcome {
        let mut rng = RandomStream::new(seed, self.limit);
        let parsed = generator(gen);
        for run in 1..=runs {
            match draw(&parsed, &mut rng) {
                None => return Outcome::GaveUp(run - 1),
                Some(value) => {
                    if !holds(prop, &value) {
                        return Outcome::Failed(run, value);
                    }
                }
            }
        }
        Outcome::Passed
    }
}
