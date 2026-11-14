use std::collections::HashMap;

const GROUP_GAP_MS: i64 = 1000;
const ROOT: usize = 0;

/// One recorded edit, kept as a command that can be applied and reverted: at `position`,
/// `removed` was replaced by `inserted`. The step is also the history state it leads to. Steps
/// live in one vector and point at each other by index, so the tree needs no shared ownership.
struct Step {
    parent: Option<usize>,
    position: usize,
    removed: String,
    inserted: String,
    children: Vec<usize>,
    current_child: Option<usize>,
}

impl Step {
    fn apply(&self, text: &str) -> String {
        let rest = &text[self.position + self.removed.len()..];
        format!("{}{}{}", &text[..self.position], self.inserted, rest)
    }

    fn revert(&self, text: &str) -> String {
        let rest = &text[self.position + self.inserted.len()..];
        format!("{}{}{}", &text[..self.position], self.removed, rest)
    }
}

pub struct Editor {
    content: String,
    steps: Vec<Step>,
    current: usize,
    checkpoints: HashMap<String, String>,
    group_open: bool,
    last_typed_at: i64,
}

impl Editor {
    pub fn new(initial: String) -> Self {
        let root = Step {
            parent: None,
            position: 0,
            removed: String::new(),
            inserted: String::new(),
            children: Vec::new(),
            current_child: None,
        };
        Editor {
            content: initial,
            steps: vec![root],
            current: ROOT,
            checkpoints: HashMap::new(),
            group_open: false,
            last_typed_at: 0,
        }
    }

    // Level 1
    pub fn insert(&mut self, position: i32, text: String) {
        self.group_open = false;
        let at = self.clamp(position);
        self.record(at, String::new(), text);
    }

    pub fn erase(&mut self, position: i32, count: i32) {
        self.group_open = false;
        let start = self.clamp(position);
        let end = self.content.len().min(start + count.max(0) as usize);
        let removed = self.content[start..end].to_string();
        self.record(start, removed, String::new());
    }

    pub fn undo(&mut self) -> bool {
        self.group_open = false;
        match self.steps[self.current].parent {
            None => false,
            Some(parent) => {
                self.content = self.steps[self.current].revert(&self.content);
                self.current = parent;
                true
            }
        }
    }

    pub fn redo(&mut self) -> bool {
        self.group_open = false;
        match self.steps[self.current].current_child {
            None => false,
            Some(child) => {
                self.content = self.steps[child].apply(&self.content);
                self.current = child;
                true
            }
        }
    }

    pub fn text(&mut self) -> String {
        self.content.clone()
    }

    // Level 2
    pub fn type_text(&mut self, timestamp: i64, position: i32, text: String) {
        let at = self.clamp(position);
        if self.joins_group(timestamp, at) {
            self.content.insert_str(at, &text);
            self.steps[self.current].inserted.push_str(&text);
        } else {
            self.record(at, String::new(), text);
        }
        self.group_open = true;
        self.last_typed_at = timestamp;
    }

    fn joins_group(&self, timestamp: i64, position: usize) -> bool {
        let group = &self.steps[self.current];
        self.group_open
            && position == group.position + group.inserted.len()
            && timestamp - self.last_typed_at <= GROUP_GAP_MS
            && !group.inserted.ends_with(' ')
    }

    // Level 3
    pub fn checkpoint(&mut self, name: String) {
        self.group_open = false;
        self.checkpoints.insert(name, self.content.clone());
    }

    pub fn restore(&mut self, name: String) -> bool {
        self.group_open = false;
        let Some(saved) = self.checkpoints.get(&name).cloned() else {
            return false;
        };
        let whole = self.content.clone();
        self.record(0, whole, saved);
        true
    }

    // Level 4
    pub fn state(&mut self) -> i32 {
        self.current as i32
    }

    pub fn branches(&mut self) -> Vec<i32> {
        self.steps[self.current].children.iter().map(|&child| child as i32).collect()
    }

    pub fn jump(&mut self, state: i32) -> bool {
        self.group_open = false;
        if state < 0 || state as usize >= self.steps.len() {
            return false;
        }
        let target = state as usize;
        let path_down = self.ancestors(target);
        while !path_down.contains(&self.current) {
            self.content = self.steps[self.current].revert(&self.content);
            self.current = self.steps[self.current].parent.expect("the root is on every path");
        }
        let common = path_down.iter().position(|&step| step == self.current).unwrap_or(0);
        for &step in path_down[..common].iter().rev() {
            self.content = self.steps[step].apply(&self.content);
        }
        for pair in path_down.windows(2) {
            self.steps[pair[1]].current_child = Some(pair[0]);
        }
        self.current = target;
        true
    }

    /// This step and every step above it, up to the root.
    fn ancestors(&self, step: usize) -> Vec<usize> {
        let mut chain = vec![step];
        while let Some(parent) = self.steps[*chain.last().unwrap_or(&ROOT)].parent {
            chain.push(parent);
        }
        chain
    }

    fn clamp(&self, position: i32) -> usize {
        (position.max(0) as usize).min(self.content.len())
    }

    /// Records one step, unless it would leave the text as it is.
    fn record(&mut self, position: usize, removed: String, inserted: String) {
        if removed == inserted {
            return;
        }
        let number = self.steps.len();
        let step = Step {
            parent: Some(self.current),
            position,
            removed,
            inserted,
            children: Vec::new(),
            current_child: None,
        };
        self.content = step.apply(&self.content);
        self.steps.push(step);
        let parent = &mut self.steps[self.current];
        parent.children.push(number);
        parent.current_child = Some(number);
        self.current = number;
    }
}
