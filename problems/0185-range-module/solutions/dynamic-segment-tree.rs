const LOW: i32 = 1;
const HIGH: i32 = 1_000_000_000; // every range lies inside [1, 10^9)

#[derive(Clone, Copy, PartialEq, Eq)]
enum State {
    Empty,
    Covered,
    Mixed,
}

/// `Empty` or `Covered` with no children, or `Mixed` with both children.
struct Node {
    state: State,
    children: Option<Box<[Node; 2]>>,
}

impl Node {
    fn new(state: State) -> Self {
        Node {
            state,
            children: None,
        }
    }

    fn assign(&mut self, low: i32, high: i32, left: i32, right: i32, value: State) {
        if right <= low || high <= left {
            return;
        }
        if left <= low && high <= right {
            self.state = value;
            self.children = None;
            return;
        }
        // A uniform node is split: both halves inherit its state.
        let state = self.state;
        let children = self
            .children
            .get_or_insert_with(|| Box::new([Node::new(state), Node::new(state)]));
        let middle = low + (high - low) / 2;
        let [first, second] = &mut **children;
        first.assign(low, middle, left, right, value);
        second.assign(middle, high, left, right, value);
        if first.state == second.state && first.state != State::Mixed {
            // Both halves agree: collapse.
            self.state = first.state;
            self.children = None;
        } else {
            self.state = State::Mixed;
        }
    }

    fn covered(&self, low: i32, high: i32, left: i32, right: i32) -> bool {
        if right <= low || high <= left {
            return true;
        }
        match &self.children {
            None => self.state == State::Covered,
            Some(children) => {
                let middle = low + (high - low) / 2;
                children[0].covered(low, middle, left, right)
                    && children[1].covered(middle, high, left, right)
            }
        }
    }
}

pub struct RangeModule {
    root: Node,
}

impl RangeModule {
    pub fn new() -> Self {
        RangeModule {
            root: Node::new(State::Empty),
        }
    }

    pub fn add_range(&mut self, left: i32, right: i32) {
        self.root.assign(LOW, HIGH, left, right, State::Covered);
    }

    pub fn query_range(&mut self, left: i32, right: i32) -> bool {
        self.root.covered(LOW, HIGH, left, right)
    }

    pub fn remove_range(&mut self, left: i32, right: i32) {
        self.root.assign(LOW, HIGH, left, right, State::Empty);
    }
}
