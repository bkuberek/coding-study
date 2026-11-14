use std::collections::{HashMap, HashSet};

// Layers are kept as given and merged on demand, oldest first, with the rules of RFC 7396. Every
// node of the merged tree remembers the layer that set it. A template is parsed in one
// left-to-right pass into a tree of text, substitutions, conditionals and loops, and rendered with
// a stack of loop bindings that shadow the values.

const BLOCK_WORDS: [&str; 4] = ["if", "else", "end", "for"];
const RESERVED: [&str; 5] = ["if", "else", "end", "for", "in"];

struct Node {
    kind: String,
    text: String,
    layer: String,
    members: HashMap<String, Node>,
    items: Vec<Node>,
}

impl Node {
    fn new(kind: &str, text: &str, layer: &str) -> Self {
        Node {
            kind: kind.to_string(),
            text: text.to_string(),
            layer: layer.to_string(),
            members: HashMap::new(),
            items: Vec::new(),
        }
    }

    fn copy_as(&self, layer: &str) -> Node {
        let mut twin = Node::new(&self.kind, &self.text, layer);
        for (key, child) in &self.members {
            twin.members.insert(key.clone(), child.copy_as(layer));
        }
        twin.items = self.items.iter().map(|child| child.copy_as(layer)).collect();
        twin
    }

    fn sorted_keys(&self) -> Vec<&String> {
        let mut keys: Vec<&String> = self.members.keys().collect();
        keys.sort();
        keys
    }
}

struct TemplateError {
    code: &'static str,
    position: usize,
    detail: String,
}

fn fail<T>(code: &'static str, position: usize) -> Result<T, TemplateError> {
    Err(TemplateError { code, position, detail: String::new() })
}

#[derive(PartialEq)]
enum Token {
    Word(String),
    Str(String),
    Punct(char),
}

enum Tag {
    Text(String),
    Out(String, Option<String>),
    If(String),
    Else,
    End,
    For(Vec<String>, String),
}

enum Segment {
    Text(String),
    Tag { tag: Tag, at: usize, trim_left: bool, trim_right: bool },
}

enum Part {
    Text(String),
    Out { path: String, fallback: Option<String>, at: usize },
    If { path: String, then: Vec<Part>, otherwise: Vec<Part> },
    For { names: Vec<String>, path: String, body: Vec<Part>, at: usize },
}

pub struct ValuesRenderer {
    names: Vec<String>,
    layers: HashMap<String, Node>,
    schema: Node,
}

impl ValuesRenderer {
    pub fn new() -> Self {
        ValuesRenderer { names: Vec::new(), layers: HashMap::new(), schema: Node::new("object", "", "") }
    }

    // Level 1
    pub fn set_layer(&mut self, name: String, rows: Vec<Vec<String>>) -> bool {
        let is_new = !self.layers.contains_key(&name);
        if is_new {
            self.names.push(name.clone());
        }
        self.layers.insert(name, decode(&rows));
        is_new
    }

    pub fn merged(&mut self) -> Vec<Vec<String>> {
        let mut rows = Vec::new();
        walk(&self.merge(), "", &mut |pointer, node| {
            rows.push(vec![pointer.to_string(), node.kind.clone(), node.text.clone()])
        });
        rows
    }

    // Level 2 and 3
    pub fn render(&mut self, template: String) -> Vec<String> {
        let values = self.merge();
        let errors = self.errors(&values);
        if !errors.is_empty() {
            return vec!["error".into(), "invalid_values".into(), String::new(), errors.len().to_string()];
        }
        let mut out = String::new();
        match parse(&template).and_then(|parts| emit(&parts, &values, &[], &mut out)) {
            Ok(()) => vec!["ok".into(), out],
            Err(error) => vec![
                "error".into(),
                error.code.to_string(),
                line_and_column(&template, error.position),
                error.detail,
            ],
        }
    }

    // Level 4
    pub fn set_schema(&mut self, rows: Vec<Vec<String>>) {
        self.schema = decode(&rows);
    }

    pub fn validate(&mut self) -> Vec<Vec<String>> {
        let values = self.merge();
        self.errors(&values)
    }

    pub fn provenance(&mut self) -> Vec<Vec<String>> {
        let mut rows = Vec::new();
        walk(&self.merge(), "", &mut |pointer, node| rows.push(vec![pointer.to_string(), node.layer.clone()]));
        rows
    }

    fn merge(&self) -> Node {
        let mut root = Node::new("object", "", "");
        for name in &self.names {
            merge_into(&mut root, &self.layers[name], name);
        }
        root
    }

    fn errors(&self, values: &Node) -> Vec<Vec<String>> {
        let mut errors = Vec::new();
        check(values, &self.schema, "", &mut errors);
        errors.sort_by(|a, b| (&a[0], &a[1]).cmp(&(&b[0], &b[1])));
        errors
    }
}

// Merging

fn decode(rows: &[Vec<String>]) -> Node {
    let mut root = Node::new("object", "", "");
    for row in rows {
        let segments: Vec<&str> = row[0].split('/').skip(1).collect();
        let (last, parents) = segments.split_last().unwrap();
        let mut parent = &mut root;
        for segment in parents {
            parent = if parent.kind == "object" {
                parent.members.get_mut(*segment).unwrap()
            } else {
                let index: usize = segment.parse().unwrap();
                &mut parent.items[index]
            };
        }
        let node = Node::new(&row[1], &row[2], "");
        if parent.kind == "object" {
            parent.members.insert(last.to_string(), node);
        } else {
            parent.items.push(node);
        }
    }
    root
}

fn walk(node: &Node, pointer: &str, visit: &mut dyn FnMut(&str, &Node)) {
    if node.kind == "object" {
        for key in node.sorted_keys() {
            let here = format!("{}/{}", pointer, key);
            let child = &node.members[key];
            visit(&here, child);
            walk(child, &here, visit);
        }
    } else if node.kind == "array" {
        for (index, child) in node.items.iter().enumerate() {
            let here = format!("{}/{}", pointer, index);
            visit(&here, child);
            walk(child, &here, visit);
        }
    }
}

fn merge_into(target: &mut Node, patch: &Node, layer: &str) {
    for (key, value) in &patch.members {
        match value.kind.as_str() {
            "null" => {
                target.members.remove(key);
            }
            "object" => {
                let keep = matches!(target.members.get(key), Some(current) if current.kind == "object");
                if !keep {
                    target.members.insert(key.clone(), Node::new("object", "", layer));
                }
                merge_into(target.members.get_mut(key).unwrap(), value, layer);
            }
            _ => {
                target.members.insert(key.clone(), value.copy_as(layer));
            }
        }
    }
}

// Parsing

fn is_key(word: &str) -> bool {
    let bytes = word.as_bytes();
    !bytes.is_empty()
        && (bytes[0].is_ascii_alphabetic() || bytes[0] == b'_')
        && bytes.iter().all(|b| b.is_ascii_alphanumeric() || *b == b'_')
}

fn is_index(word: &str) -> bool {
    let bytes = word.as_bytes();
    !bytes.is_empty() && bytes.iter().all(|b| b.is_ascii_digit()) && (word == "0" || bytes[0] != b'0')
}

fn is_path(word: &str) -> bool {
    word.split('.').all(|segment| is_key(segment) || is_index(segment))
}

fn is_word_char(c: u8) -> bool {
    c.is_ascii_alphanumeric() || c == b'_' || c == b'.'
}

fn tokenize(body: &str, position: usize) -> Result<Vec<Token>, TemplateError> {
    let bytes = body.as_bytes();
    let mut tokens = Vec::new();
    let mut i = 0;
    while i < bytes.len() {
        let c = bytes[i];
        if c == b' ' {
            i += 1;
        } else if c == b'|' || c == b',' {
            tokens.push(Token::Punct(c as char));
            i += 1;
        } else if c == b'"' {
            let mut text = String::new();
            i += 1;
            loop {
                if i >= bytes.len() {
                    return fail("bad_expression", position);
                }
                let d = bytes[i];
                if d == b'"' {
                    break;
                }
                if d == b'\\' {
                    match bytes.get(i + 1) {
                        Some(next) if *next == b'"' || *next == b'\\' => text.push(*next as char),
                        _ => return fail("bad_expression", position),
                    }
                    i += 2;
                } else {
                    text.push(d as char);
                    i += 1;
                }
            }
            tokens.push(Token::Str(text));
            i += 1;
        } else if is_word_char(c) {
            let start = i;
            while i < bytes.len() && is_word_char(bytes[i]) {
                i += 1;
            }
            tokens.push(Token::Word(body[start..i].to_string()));
        } else {
            return fail("bad_expression", position);
        }
    }
    Ok(tokens)
}

fn classify(tokens: &[Token], position: usize) -> Result<Tag, TemplateError> {
    if let Some(Token::Word(head)) = tokens.first() {
        if BLOCK_WORDS.contains(&head.as_str()) {
            return classify_block(tokens, position);
        }
    }
    match tokens {
        [Token::Str(text)] => Ok(Tag::Text(text.clone())),
        [Token::Word(path)] if is_path(path) => Ok(Tag::Out(path.clone(), None)),
        [Token::Word(path), Token::Punct('|'), Token::Word(filter), Token::Str(text)]
            if is_path(path) && filter == "default" =>
        {
            Ok(Tag::Out(path.clone(), Some(text.clone())))
        }
        _ => fail("bad_expression", position),
    }
}

fn is_name(word: &str) -> bool {
    is_key(word) && !RESERVED.contains(&word)
}

fn classify_block(tokens: &[Token], position: usize) -> Result<Tag, TemplateError> {
    let word = |s: &str| Token::Word(s.to_string());
    match tokens {
        [only] if *only == word("else") => Ok(Tag::Else),
        [only] if *only == word("end") => Ok(Tag::End),
        [head, Token::Word(path)] if *head == word("if") && is_path(path) => Ok(Tag::If(path.clone())),
        [head, Token::Word(name), inn, Token::Word(path)]
            if *head == word("for") && *inn == word("in") && is_name(name) && is_path(path) =>
        {
            Ok(Tag::For(vec![name.clone()], path.clone()))
        }
        [head, Token::Word(key), Token::Punct(','), Token::Word(name), inn, Token::Word(path)]
            if *head == word("for")
                && *inn == word("in")
                && is_name(key)
                && is_name(name)
                && key != name
                && is_path(path) =>
        {
            Ok(Tag::For(vec![key.clone(), name.clone()], path.clone()))
        }
        _ => fail("bad_expression", position),
    }
}

fn parse(template: &str) -> Result<Vec<Part>, TemplateError> {
    let mut segments: Vec<Segment> = Vec::new();
    let mut stack: Vec<(bool, usize, bool)> = Vec::new(); // (is if, position, has else)
    let mut i = 0;
    loop {
        let start = match template[i..].find("{{") {
            Some(offset) => i + offset,
            None => {
                segments.push(Segment::Text(template[i..].to_string()));
                break;
            }
        };
        segments.push(Segment::Text(template[i..start].to_string()));
        let end = match template[start + 2..].find("}}") {
            Some(offset) => start + 2 + offset,
            None => return fail("unclosed_tag", start),
        };
        let mut body = &template[start + 2..end];
        let trim_left = body.starts_with('-');
        if trim_left {
            body = &body[1..];
        }
        let trim_right = body.ends_with('-');
        if trim_right {
            body = &body[..body.len() - 1];
        }
        let tag = classify(&tokenize(body.trim_matches(' '), start)?, start)?;
        match &tag {
            Tag::If(_) => stack.push((true, start, false)),
            Tag::For(_, _) => stack.push((false, start, false)),
            Tag::Else => match stack.last_mut() {
                Some(top) if top.0 && !top.2 => top.2 = true,
                _ => return fail("unexpected_tag", start),
            },
            Tag::End => {
                if stack.pop().is_none() {
                    return fail("unexpected_tag", start);
                }
            }
            _ => {}
        }
        segments.push(Segment::Tag { tag, at: start, trim_left, trim_right });
        i = end + 2;
    }
    if let Some(top) = stack.last() {
        return fail("unclosed_block", top.1);
    }
    for k in 0..segments.len() {
        let (left, right) = match &segments[k] {
            Segment::Tag { trim_left, trim_right, .. } => (*trim_left, *trim_right),
            Segment::Text(_) => continue,
        };
        if left {
            if let Segment::Text(text) = &mut segments[k - 1] {
                *text = text.trim_end_matches([' ', '\n']).to_string();
            }
        }
        if right {
            if let Segment::Text(text) = &mut segments[k + 1] {
                *text = text.trim_start_matches([' ', '\n']).to_string();
            }
        }
    }
    let mut cursor = 0;
    Ok(build(&segments, &mut cursor))
}

/// Builds parts from `segments[*cursor..]` up to the else or end that closes the current block,
/// leaving the cursor on it. The block structure was checked by the scan.
fn build(segments: &[Segment], cursor: &mut usize) -> Vec<Part> {
    let mut parts = Vec::new();
    while *cursor < segments.len() {
        match &segments[*cursor] {
            Segment::Text(text) => {
                if !text.is_empty() {
                    parts.push(Part::Text(text.clone()));
                }
            }
            Segment::Tag { tag, at, .. } => match tag {
                Tag::Else | Tag::End => return parts,
                Tag::Text(text) => parts.push(Part::Text(text.clone())),
                Tag::Out(path, fallback) => {
                    parts.push(Part::Out { path: path.clone(), fallback: fallback.clone(), at: *at })
                }
                Tag::If(path) => {
                    *cursor += 1;
                    let then = build(segments, cursor);
                    let mut otherwise = Vec::new();
                    if matches!(segments[*cursor], Segment::Tag { tag: Tag::Else, .. }) {
                        *cursor += 1;
                        otherwise = build(segments, cursor);
                    }
                    parts.push(Part::If { path: path.clone(), then, otherwise });
                }
                Tag::For(names, path) => {
                    *cursor += 1;
                    let body = build(segments, cursor);
                    parts.push(Part::For { names: names.clone(), path: path.clone(), body, at: *at });
                }
            },
        }
        *cursor += 1;
    }
    parts
}

fn line_and_column(template: &str, position: usize) -> String {
    let before = &template[..position];
    let line = before.matches('\n').count() + 1;
    let column = position - before.rfind('\n').map_or(0, |at| at + 1) + 1;
    format!("{}:{}", line, column)
}

// Rendering

fn emit<'a>(parts: &[Part], values: &'a Node, scope: &[(&'a str, &'a Node)], out: &mut String) -> Result<(), TemplateError> {
    for part in parts {
        match part {
            Part::Text(text) => out.push_str(text),
            Part::Out { path, fallback, at } => match (lookup(path, values, scope), fallback) {
                (None, Some(text)) => out.push_str(text),
                (None, None) => {
                    return Err(TemplateError { code: "missing_value", position: *at, detail: path.clone() })
                }
                (Some(found), _) if found.kind == "object" || found.kind == "array" => {
                    return Err(TemplateError { code: "not_scalar", position: *at, detail: path.clone() })
                }
                (Some(found), _) => out.push_str(&found.text),
            },
            Part::If { path, then, otherwise } => {
                let branch = if truthy(lookup(path, values, scope)) { then } else { otherwise };
                emit(branch, values, scope, out)?;
            }
            Part::For { names, path, body, at } => run_loop(names, path, body, *at, values, scope, out)?,
        }
    }
    Ok(())
}

fn run_loop<'a>(
    names: &[String],
    path: &str,
    body: &[Part],
    at: usize,
    values: &'a Node,
    scope: &[(&'a str, &'a Node)],
    out: &mut String,
) -> Result<(), TemplateError> {
    let error = |code| Err(TemplateError { code, position: at, detail: path.to_string() });
    let found = match lookup(path, values, scope) {
        Some(found) => found,
        None => return error("missing_value"),
    };
    let pairs: Vec<(Node, &'a Node)> = match found.kind.as_str() {
        "array" => found.items.iter().enumerate().map(|(i, item)| (Node::new("number", &i.to_string(), ""), item)).collect(),
        "object" => found.sorted_keys().into_iter().map(|key| (Node::new("string", key, ""), &found.members[key])).collect(),
        _ => return error("not_iterable"),
    };
    for (key, item) in &pairs {
        let mut inner: Vec<(&str, &Node)> = scope.to_vec();
        if names.len() == 2 {
            inner.push((names[0].as_str(), key));
            inner.push((names[1].as_str(), *item));
        } else {
            inner.push((names[0].as_str(), *item));
        }
        emit(body, values, &inner, out)?;
    }
    Ok(())
}

fn lookup<'a>(path: &str, values: &'a Node, scope: &[(&'a str, &'a Node)]) -> Option<&'a Node> {
    let segments: Vec<&str> = path.split('.').collect();
    let mut current = values;
    let mut rest: &[&str] = &segments;
    if let Some((_, bound)) = scope.iter().rev().find(|(name, _)| *name == segments[0]) {
        current = *bound;
        rest = &segments[1..];
    }
    for segment in rest {
        current = match current.kind.as_str() {
            "object" => current.members.get(*segment)?,
            "array" if is_index(segment) => current.items.get(segment.parse::<usize>().ok()?)?,
            _ => return None,
        };
    }
    if current.kind == "null" {
        None
    } else {
        Some(current)
    }
}

fn truthy(node: Option<&Node>) -> bool {
    match node {
        None => false,
        Some(node) => match node.kind.as_str() {
            "boolean" => node.text == "true",
            "string" => !node.text.is_empty(),
            "number" => node.text != "0",
            "object" => !node.members.is_empty(),
            _ => !node.items.is_empty(),
        },
    }
}

// Validation

fn has_type(node: &Node, name: &str) -> bool {
    node.kind == name || (name == "integer" && node.kind == "number")
}

fn is_listed(node: &Node, options: &Node) -> bool {
    node.kind != "object"
        && node.kind != "array"
        && options.items.iter().any(|option| option.kind == node.kind && option.text == node.text)
}

fn check(node: &Node, schema: &Node, pointer: &str, errors: &mut Vec<Vec<String>>) {
    let keywords = &schema.members;
    let mut fail = |at: String, keyword: &str, layer: &str| errors.push(vec![at, keyword.to_string(), layer.to_string()]);
    if let Some(name) = keywords.get("type") {
        if !has_type(node, &name.text) {
            fail(pointer.to_string(), "type", &node.layer);
        }
    }
    if let Some(options) = keywords.get("enum") {
        if !is_listed(node, options) {
            fail(pointer.to_string(), "enum", &node.layer);
        }
    }
    if node.kind == "number" {
        let value: i64 = node.text.parse().unwrap();
        if let Some(minimum) = keywords.get("minimum") {
            if value < minimum.text.parse::<i64>().unwrap() {
                fail(pointer.to_string(), "minimum", &node.layer);
            }
        }
        if let Some(maximum) = keywords.get("maximum") {
            if value > maximum.text.parse::<i64>().unwrap() {
                fail(pointer.to_string(), "maximum", &node.layer);
            }
        }
    }
    let mut nested: Vec<(&Node, &Node, String)> = Vec::new();
    if node.kind == "object" {
        if let Some(required) = keywords.get("required") {
            for key in &required.items {
                if !node.members.contains_key(&key.text) {
                    fail(format!("{}/{}", pointer, key.text), "required", "");
                }
            }
        }
        let closed = keywords.get("additionalProperties").map_or(false, |value| value.text == "false");
        let properties = keywords.get("properties");
        let listed: HashSet<&String> = properties.map_or(HashSet::new(), |p| p.members.keys().collect());
        for (key, child) in &node.members {
            if listed.contains(key) {
                nested.push((child, &properties.unwrap().members[key], format!("{}/{}", pointer, key)));
            } else if closed {
                fail(format!("{}/{}", pointer, key), "additionalProperties", &child.layer);
            }
        }
    }
    if let (Some(items), "array") = (keywords.get("items"), node.kind.as_str()) {
        for (index, child) in node.items.iter().enumerate() {
            nested.push((child, items, format!("{}/{}", pointer, index)));
        }
    }
    for (child, sub, at) in nested {
        check(child, sub, &at, errors);
    }
}
