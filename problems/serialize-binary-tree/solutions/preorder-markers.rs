use std::cell::RefCell;
use std::rc::Rc;
use std::str::Split;

use cs_support::TreeNode;

type Tree = Option<Rc<RefCell<TreeNode>>>;

const MISSING: &str = "#";
const SEPARATOR: &str = ",";

pub fn serialize_deserialize(root: Option<Rc<RefCell<TreeNode>>>) -> Option<Rc<RefCell<TreeNode>>> {
    deserialize(&serialize(&root))
}

fn serialize(root: &Tree) -> String {
    let mut tokens = Vec::new();
    write(root, &mut tokens);
    tokens.join(SEPARATOR)
}

fn write(node: &Tree, tokens: &mut Vec<String>) {
    match node {
        None => tokens.push(MISSING.to_string()),
        Some(node) => {
            let node = node.borrow();
            tokens.push(node.val.to_string());
            write(&node.left, tokens);
            write(&node.right, tokens);
        }
    }
}

fn deserialize(data: &str) -> Tree {
    read(&mut data.split(SEPARATOR))
}

/// Hands out the tokens of one string in order, rebuilding the tree in pre-order.
fn read(tokens: &mut Split<'_, &str>) -> Tree {
    let token = tokens.next().expect("a token for every node and marker");
    if token == MISSING {
        return None;
    }
    let mut node = TreeNode::new(token.parse().expect("an integer token"));
    node.left = read(tokens);
    node.right = read(tokens);
    Some(Rc::new(RefCell::new(node)))
}
