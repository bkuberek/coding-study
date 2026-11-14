use std::cell::RefCell;
use std::collections::VecDeque;
use std::rc::Rc;

use cs_support::TreeNode;

type Tree = Option<Rc<RefCell<TreeNode>>>;

const MISSING: &str = "#";
const SEPARATOR: &str = ",";

pub fn serialize_deserialize(root: Option<Rc<RefCell<TreeNode>>>) -> Option<Rc<RefCell<TreeNode>>> {
    deserialize(&serialize(root))
}

fn serialize(root: Tree) -> String {
    let mut tokens = Vec::new();
    let mut queue = VecDeque::from([root]);
    while let Some(node) = queue.pop_front() {
        match node {
            None => tokens.push(MISSING.to_string()),
            Some(node) => {
                let node = node.borrow();
                tokens.push(node.val.to_string());
                queue.push_back(node.left.clone());
                queue.push_back(node.right.clone());
            }
        }
    }
    tokens.join(SEPARATOR)
}

fn deserialize(data: &str) -> Tree {
    let mut tokens = data.split(SEPARATOR);
    let mut next_node = || {
        let token = tokens.next().expect("a token for every node and marker");
        if token == MISSING {
            return None;
        }
        let value = token.parse().expect("an integer token");
        Some(Rc::new(RefCell::new(TreeNode::new(value))))
    };
    let root = next_node();
    let mut queue: VecDeque<_> = root.iter().cloned().collect();
    // Every node was written with exactly two child tokens, in queue order.
    while let Some(node) = queue.pop_front() {
        let left = next_node();
        let right = next_node();
        queue.extend(left.iter().chain(right.iter()).cloned());
        let mut node = node.borrow_mut();
        node.left = left;
        node.right = right;
    }
    root
}
