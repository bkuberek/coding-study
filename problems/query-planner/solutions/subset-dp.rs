use std::collections::{HashMap, HashSet};

const KEYWORDS: [&str; 6] = ["SELECT", "FROM", "JOIN", "ON", "WHERE", "AND"];
const RANDOM_READ: i64 = 4;

#[derive(Clone, PartialEq)]
struct Column {
    table: String,
    name: String,
}

impl Column {
    fn dotted(&self) -> String {
        format!("{}.{}", self.table, self.name)
    }
}

#[derive(Clone, PartialEq)]
struct Condition {
    column: Column,
    op: String,
    value: String,
}

impl Condition {
    fn show(&self) -> String {
        format!("{} {} {}", self.column.dotted(), self.op, self.value)
    }
}

fn is_letter(c: u8) -> bool {
    c.is_ascii_alphabetic() || c == b'_'
}

fn tokenize(sql: &str) -> Option<Vec<String>> {
    let bytes = sql.as_bytes();
    let mut tokens = Vec::new();
    let mut i = 0;
    while i < bytes.len() {
        let c = bytes[i];
        if c == b' ' {
            i += 1;
        } else if is_letter(c) {
            let mut j = i + 1;
            while j < bytes.len() && (is_letter(bytes[j]) || bytes[j].is_ascii_digit()) {
                j += 1;
            }
            tokens.push(sql[i..j].to_string());
            i = j;
        } else if c.is_ascii_digit() || (c == b'-' && i + 1 < bytes.len() && bytes[i + 1].is_ascii_digit()) {
            let mut j = i + 1;
            while j < bytes.len() && bytes[j].is_ascii_digit() {
                j += 1;
            }
            let sign = if c == b'-' { 1 } else { 0 };
            if j - i - sign > 9 {
                return None;
            }
            tokens.push(sql[i..j].to_string());
            i = j;
        } else if b"*,.=<>".contains(&c) {
            tokens.push((c as char).to_string());
            i += 1;
        } else {
            return None;
        }
    }
    Some(tokens)
}

/// SELECT ... FROM t [JOIN u ON a.x = b.y]... [WHERE c op n [AND ...]], as written.
struct Query {
    selected: Option<Vec<Column>>,
    tables: Vec<String>,
    joins: Vec<(Column, Column)>,
    conditions: Vec<Condition>,
}

struct Parser {
    tokens: Vec<String>,
    pos: usize,
}

impl Parser {
    fn peek(&self) -> &str {
        self.tokens.get(self.pos).map_or("", |token| token.as_str())
    }

    fn expect(&mut self, token: &str) -> Option<()> {
        if self.peek() != token {
            return None;
        }
        self.pos += 1;
        Some(())
    }

    fn name(&mut self) -> Option<String> {
        let token = self.peek().to_string();
        if token.is_empty() || !is_letter(token.as_bytes()[0]) || KEYWORDS.contains(&token.as_str()) {
            return None;
        }
        self.pos += 1;
        Some(token)
    }

    fn column(&mut self) -> Option<Column> {
        let table = self.name()?;
        self.expect(".")?;
        Some(Column { table, name: self.name()? })
    }

    fn condition(&mut self) -> Option<Condition> {
        let column = self.column()?;
        let op = self.peek().to_string();
        if op != "=" && op != "<" && op != ">" {
            return None;
        }
        self.pos += 1;
        let value = self.peek().to_string();
        let first = *value.as_bytes().first()?;
        if !(first.is_ascii_digit() || first == b'-') {
            return None;
        }
        self.pos += 1;
        Some(Condition { column, op, value })
    }

    fn query(&mut self) -> Option<Query> {
        self.expect("SELECT")?;
        let mut selected = None;
        if self.peek() == "*" {
            self.pos += 1;
        } else {
            let mut chosen = vec![self.column()?];
            while self.peek() == "," {
                self.pos += 1;
                chosen.push(self.column()?);
            }
            selected = Some(chosen);
        }
        self.expect("FROM")?;
        let mut tables = vec![self.name()?];
        let mut joins = Vec::new();
        while self.peek() == "JOIN" {
            self.pos += 1;
            tables.push(self.name()?);
            self.expect("ON")?;
            let left = self.column()?;
            self.expect("=")?;
            joins.push((left, self.column()?));
        }
        let mut conditions = Vec::new();
        if self.peek() == "WHERE" {
            self.pos += 1;
            conditions.push(self.condition()?);
            while self.peek() == "AND" {
                self.pos += 1;
                conditions.push(self.condition()?);
            }
        }
        if self.pos != self.tokens.len() {
            return None;
        }
        Some(Query { selected, tables, joins, conditions })
    }
}

/// numerator / denominator rounded half up, and at least 1.
fn rounded(numerator: i64, denominator: i64) -> i64 {
    ((2 * numerator + denominator) / (2 * denominator)).max(1)
}

struct Edge {
    left: usize,
    right: usize,
    left_column: Column,
    right_column: Column,
}

/// One checked query: tables in written order (a table is its position, a set of tables a bit
/// mask), the conditions of each table, and one edge per join, written with the earlier table
/// first.
struct Plan<'a> {
    planner: &'a QueryPlanner,
    selected: Option<Vec<Column>>,
    tables: Vec<String>,
    conditions: Vec<Vec<Condition>>,
    edges: Vec<Edge>,
}

impl<'a> Plan<'a> {
    fn new(planner: &'a QueryPlanner, sql: &str, need_stats: bool) -> Result<Plan<'a>, String> {
        let tokens = tokenize(sql).ok_or("syntax")?;
        let query = Parser { tokens, pos: 0 }.query().ok_or("syntax")?;
        let mut seen: Vec<String> = Vec::new();
        for table in &query.tables {
            if !planner.columns.contains_key(table) {
                return Err(format!("unknown-table {}", table));
            }
            if seen.contains(table) {
                return Err(format!("duplicate-table {}", table));
            }
            seen.push(table.clone());
        }
        let mut refs: Vec<&Column> = query.selected.iter().flatten().collect();
        for (left, right) in &query.joins {
            refs.push(left);
            refs.push(right);
        }
        refs.extend(query.conditions.iter().map(|c| &c.column));
        for column in refs {
            if !seen.contains(&column.table) || !planner.columns[&column.table].contains(&column.name) {
                return Err(format!("unknown-column {}", column.dotted()));
            }
        }
        let mut edges = Vec::new();
        for (index, (first, second)) in query.joins.iter().enumerate() {
            let table = &query.tables[index + 1];
            let earlier = &query.tables[..=index];
            let (left, right) = if &first.table == table && earlier.contains(&second.table) {
                (second, first)
            } else if &second.table == table && earlier.contains(&first.table) {
                (first, second)
            } else {
                return Err(format!("bad-join {}", table));
            };
            let position = query.tables.iter().position(|t| *t == left.table).unwrap();
            edges.push(Edge { left: position, right: index + 1, left_column: left.clone(), right_column: right.clone() });
        }
        if need_stats {
            for table in &query.tables {
                if !planner.stats.contains_key(table) {
                    return Err(format!("no-stats {}", table));
                }
            }
        }
        let conditions: Vec<Vec<Condition>> = query
            .tables
            .iter()
            .map(|table| query.conditions.iter().filter(|c| &c.column.table == table).cloned().collect())
            .collect();
        Ok(Plan { planner, selected: query.selected, tables: query.tables, conditions, edges })
    }

    fn head(&self) -> String {
        match &self.selected {
            None => "project *".to_string(),
            Some(columns) => {
                let names: Vec<String> = columns.iter().map(|c| c.dotted()).collect();
                format!("project {}", names.join(", "))
            }
        }
    }

    // --- estimates
    fn distinct(&self, column: &Column) -> i64 {
        let position = self.planner.columns[&column.table].iter().position(|c| *c == column.name).unwrap();
        self.planner.stats[&column.table].1[position]
    }

    fn divisor(&self, condition: &Condition) -> i64 {
        if condition.op == "=" {
            self.distinct(&condition.column)
        } else {
            3
        }
    }

    fn base(&self, table: usize) -> i64 {
        self.planner.stats[&self.tables[table]].0
    }

    /// The rows of a table after its conditions.
    fn out(&self, table: usize) -> i64 {
        if self.conditions[table].is_empty() {
            return self.base(table);
        }
        let divisor: i64 = self.conditions[table].iter().map(|c| self.divisor(c)).product();
        rounded(self.base(table), divisor)
    }

    fn rows(&self, mask: usize) -> i64 {
        let numerator: i64 = (0..self.tables.len()).filter(|t| mask & (1 << t) != 0).map(|t| self.out(t)).product();
        let denominator: i64 = self
            .edges
            .iter()
            .filter(|e| mask & (1 << e.left) != 0 && mask & (1 << e.right) != 0)
            .map(|e| self.distinct(&e.left_column).max(self.distinct(&e.right_column)))
            .product();
        rounded(numerator, denominator)
    }

    /// The edge between a table and a set it joins, written with the set's column first.
    fn edge_into(&self, mask: usize, table: usize) -> Option<(&Column, &Column)> {
        for e in &self.edges {
            if e.right == table && mask & (1 << e.left) != 0 {
                return Some((&e.left_column, &e.right_column));
            }
            if e.left == table && mask & (1 << e.right) != 0 {
                return Some((&e.right_column, &e.left_column));
            }
        }
        None
    }

    // --- level 4 access paths and join methods
    /// The cheapest way to read a table: its cost, and the position of the condition an index
    /// serves, or None for a full scan. Ties keep the full scan, then the condition written first.
    fn access(&self, table: usize) -> (i64, Option<usize>) {
        let mut best = (self.base(table), None);
        let empty = HashSet::new();
        let indexed = self.planner.indexes.get(&self.tables[table]).unwrap_or(&empty);
        for (position, condition) in self.conditions[table].iter().enumerate() {
            if condition.op == "=" && indexed.contains(&condition.column.name) {
                let cost = RANDOM_READ * rounded(self.base(table), self.distinct(&condition.column));
                if cost < best.0 {
                    best = (cost, Some(position));
                }
            }
        }
        best
    }

    fn join_step(&self, left_rows: i64, table: usize) -> (&'static str, i64) {
        let inner_cost = self.access(table).0;
        let nested = left_rows * inner_cost;
        let hashed = inner_cost + self.out(table) + left_rows;
        if nested <= hashed {
            ("nested loop", nested)
        } else {
            ("hash join", hashed)
        }
    }

    // --- printing
    fn table_lines(&self, table: usize, depth: usize, mode: u8) -> Vec<String> {
        let pad = "  ".repeat(depth);
        let name = &self.tables[table];
        let mut conditions: Vec<&Condition> = self.conditions[table].iter().collect();
        let scan = match mode {
            1 => format!("scan {}", name),
            2 | 3 => format!("scan {} (rows={})", name, self.base(table)),
            _ => match self.access(table) {
                (cost, None) => format!("full scan {} (rows={} cost={})", name, self.base(table), cost),
                (cost, Some(used)) => {
                    let condition = conditions.remove(used);
                    let matched = rounded(self.base(table), self.distinct(&condition.column));
                    format!("index scan {} (rows={} cost={})", condition.show(), matched, cost)
                }
            },
        };
        if conditions.is_empty() {
            return vec![pad + &scan];
        }
        let shown: Vec<String> = conditions.iter().map(|c| c.show()).collect();
        let mut filter = format!("filter {}", shown.join(" AND "));
        if mode > 1 {
            filter += &format!(" (rows={})", self.out(table));
        }
        vec![format!("{}{}", pad, filter), format!("{}  {}", pad, scan)]
    }

    /// The plan joining the tables in this order, left-deep, under its project line. Mode 1
    /// prints no numbers, 2 the rows, 3 the rows and the cost, 4 the access paths and the join
    /// methods.
    fn lines(&self, order: &[usize], mode: u8) -> Vec<String> {
        let depth = order.len();
        let mut steps = Vec::new();
        let mut joined = 1usize << order[0];
        let mut cost = if mode == 4 { self.access(order[0]).0 } else { 0 };
        for &table in &order[1..] {
            let (left_column, right_column) = self.edge_into(joined, table).unwrap();
            let mut name = "join";
            if mode == 4 {
                let (method, step) = self.join_step(self.rows(joined), table);
                name = method;
                cost += step;
            }
            joined |= 1 << table;
            if mode == 3 {
                cost += self.rows(joined);
            }
            let mut text = format!("{} {} = {}", name, left_column.dotted(), right_column.dotted());
            if mode == 2 {
                text += &format!(" (rows={})", self.rows(joined));
            } else if mode > 2 {
                text += &format!(" (rows={} cost={})", self.rows(joined), cost);
            }
            steps.push(text);
        }
        // Pre-order: the last join on top, each join's left input below it, then the first table;
        // the table joined at step k is the right input of that join, at depth n - k + 1.
        let mut result = vec![self.head()];
        for (level, text) in steps.iter().rev().enumerate() {
            result.push(format!("{}{}", "  ".repeat(level + 1), text));
        }
        result.extend(self.table_lines(order[0], depth, mode));
        for k in 1..order.len() {
            result.extend(self.table_lines(order[k], depth - k + 1, mode));
        }
        result
    }

    fn before(&self, a: &(i64, Vec<usize>), b: &(i64, Vec<usize>)) -> bool {
        if a.0 != b.0 {
            return a.0 < b.0;
        }
        let names = |order: &Vec<usize>| order.iter().map(|&t| self.tables[t].clone()).collect::<Vec<_>>();
        names(&a.1) < names(&b.1)
    }

    /// Dynamic programming over subsets: the cheapest left-deep order of every connected set,
    /// built from the cheapest order of the set without its last table. Ties go to the order
    /// whose list of table names comes first.
    fn best_order(&self, mode: u8) -> Vec<usize> {
        let count = self.tables.len();
        let mut best: Vec<Option<(i64, Vec<usize>)>> = vec![None; 1 << count];
        for t in 0..count {
            let cost = if mode == 4 { self.access(t).0 } else { 0 };
            best[1 << t] = Some((cost, vec![t]));
        }
        for size in 2..=count {
            for mask in 1..(1usize << count) {
                let known = match &best[mask] {
                    Some(known) if known.1.len() == size - 1 => known.clone(),
                    _ => continue,
                };
                for t in 0..count {
                    if mask & (1 << t) != 0 || self.edge_into(mask, t).is_none() {
                        continue;
                    }
                    let grown = mask | (1 << t);
                    let step = if mode == 4 { self.join_step(self.rows(mask), t).1 } else { self.rows(grown) };
                    let mut order = known.1.clone();
                    order.push(t);
                    let candidate = (known.0 + step, order);
                    let better = match &best[grown] {
                        None => true,
                        Some(current) => self.before(&candidate, current),
                    };
                    if better {
                        best[grown] = Some(candidate);
                    }
                }
            }
        }
        best[(1 << count) - 1].take().unwrap().1
    }
}

/// Parses a small SQL subset, checks it against the catalog, and plans it: written order with
/// filters pushed to the scans, row estimates from table statistics, the cheapest left-deep join
/// order by dynamic programming over subsets of tables, then access paths and join methods.
pub struct QueryPlanner {
    columns: HashMap<String, Vec<String>>,
    stats: HashMap<String, (i64, Vec<i64>)>,
    indexes: HashMap<String, HashSet<String>>,
}

impl QueryPlanner {
    pub fn new() -> Self {
        QueryPlanner { columns: HashMap::new(), stats: HashMap::new(), indexes: HashMap::new() }
    }

    fn plan(&self, sql: &str, need_stats: bool, mode: u8) -> Vec<String> {
        match Plan::new(self, sql, need_stats) {
            Err(failure) => vec![format!("error: {}", failure)],
            Ok(plan) => {
                let order = if mode >= 3 { plan.best_order(mode) } else { (0..plan.tables.len()).collect() };
                plan.lines(&order, mode)
            }
        }
    }

    // Level 1
    pub fn add_table(&mut self, table: String, columns: Vec<String>) -> String {
        if self.columns.contains_key(&table) {
            return "duplicate".to_string();
        }
        self.columns.insert(table, columns);
        "ok".to_string()
    }

    pub fn logical_plan(&mut self, sql: String) -> Vec<String> {
        self.plan(&sql, false, 1)
    }

    // Level 2
    pub fn analyze(&mut self, table: String, rows: i64, distinct: Vec<i64>) -> String {
        let columns = match self.columns.get(&table) {
            None => return "unknown-table".to_string(),
            Some(columns) => columns,
        };
        if distinct.len() != columns.len() || rows < 1 || distinct.iter().any(|&c| c < 1 || c > rows) {
            return "bad-stats".to_string();
        }
        self.stats.insert(table, (rows, distinct));
        "ok".to_string()
    }

    pub fn estimate(&mut self, sql: String) -> Vec<String> {
        self.plan(&sql, true, 2)
    }

    // Level 3
    pub fn optimize(&mut self, sql: String) -> Vec<String> {
        self.plan(&sql, true, 3)
    }

    // Level 4
    pub fn add_index(&mut self, table: String, column: String) -> String {
        let columns = match self.columns.get(&table) {
            None => return "unknown-table".to_string(),
            Some(columns) => columns,
        };
        if !columns.contains(&column) {
            return "unknown-column".to_string();
        }
        if !self.indexes.entry(table).or_default().insert(column) {
            return "duplicate".to_string();
        }
        "ok".to_string()
    }

    pub fn explain(&mut self, sql: String) -> Vec<String> {
        self.plan(&sql, true, 4)
    }
}
