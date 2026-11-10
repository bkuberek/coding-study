const ARROW_DOWN: &str = "ArrowDown";
const ARROW_UP: &str = "ArrowUp";
const ENTER: &str = "Enter";
const NOTHING: i32 = -1;

/// The list is empty exactly when nothing is highlighted: `show` keeps the two in step.
pub struct SearchBox {
    names: Vec<String>,
    lowered_names: Vec<String>,
    shown: Vec<String>,
    highlight: Option<usize>,
    text: String,
    requests_sent: i32,
    awaited_request: Option<i32>,
    selected: Vec<String>,
}

impl SearchBox {
    pub fn new(names: Vec<String>) -> Self {
        let lowered_names = names.iter().map(|name| name.to_lowercase()).collect();
        SearchBox {
            names,
            lowered_names,
            shown: Vec::new(),
            highlight: None,
            text: String::new(),
            requests_sent: 0,
            awaited_request: None,
            selected: Vec::new(),
        }
    }

    // Level 1
    pub fn keydown(&mut self, _timestamp: i64, key: String) {
        match key.as_str() {
            ARROW_DOWN => self.move_by(1),
            ARROW_UP => self.move_by(-1),
            ENTER => self.select_highlighted(),
            _ => {}
        }
    }

    /// Releasing a key changes nothing: every action happens when the key goes down.
    pub fn keyup(&mut self, _timestamp: i64, _key: String) {}

    pub fn results_arrived(&mut self, _timestamp: i64, items: Vec<String>) {
        self.show(items);
    }

    pub fn results(&mut self, _timestamp: i64) -> Vec<String> {
        self.shown.clone()
    }

    pub fn highlighted(&mut self, _timestamp: i64) -> i32 {
        self.highlight.map_or(NOTHING, |position| position as i32)
    }

    pub fn highlighted_text(&mut self, _timestamp: i64) -> String {
        self.highlight
            .map_or_else(String::new, |position| self.shown[position].clone())
    }

    // Level 2
    pub fn search(&mut self, _timestamp: i64, query: String) {
        let needle = query.trim().to_lowercase();
        let matches = if needle.is_empty() {
            Vec::new()
        } else {
            self.names
                .iter()
                .zip(&self.lowered_names)
                .filter(|(_, lowered)| lowered.contains(&needle))
                .map(|(name, _)| name.clone())
                .collect()
        };
        self.show(matches);
    }

    // Level 3
    pub fn input_changed(&mut self, _timestamp: i64, text: String) -> i32 {
        let blank = text.trim().is_empty();
        self.text = text;
        if blank {
            self.stop_awaiting();
            return NOTHING;
        }
        self.requests_sent += 1;
        self.awaited_request = Some(self.requests_sent);
        self.requests_sent
    }

    pub fn response_arrived(&mut self, _timestamp: i64, request_id: i32, items: Vec<String>) {
        if self.awaited_request == Some(request_id) {
            self.show(items);
        }
    }

    pub fn input_text(&mut self, _timestamp: i64) -> String {
        self.text.clone()
    }

    // Level 4
    pub fn selections(&mut self, _timestamp: i64) -> Vec<String> {
        self.selected.clone()
    }

    /// `rem_euclid` never returns a negative remainder, unlike `%`.
    fn move_by(&mut self, step: i64) {
        let count = self.shown.len() as i64;
        if let Some(position) = self.highlight {
            self.highlight = Some((position as i64 + step).rem_euclid(count) as usize);
        }
    }

    fn select_highlighted(&mut self) {
        let Some(position) = self.highlight else {
            return;
        };
        let choice = self.shown[position].clone();
        self.selected.push(choice.clone());
        self.text = choice;
        self.stop_awaiting();
    }

    /// The input changed without a request: no response sent so far may be shown, and the list
    /// closes.
    fn stop_awaiting(&mut self) {
        self.awaited_request = None;
        self.show(Vec::new());
    }

    fn show(&mut self, items: Vec<String>) {
        self.highlight = if items.is_empty() { None } else { Some(0) };
        self.shown = items;
    }
}
