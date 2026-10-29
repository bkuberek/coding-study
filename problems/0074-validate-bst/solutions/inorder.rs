use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn is_valid_bst(root: Option<Rc<RefCell<TreeNode>>>) -> bool {
    let mut stack: Vec<Rc<RefCell<TreeNode>>> = Vec::new();
    let mut node = root;
    let mut previous: Option<i32> = None;
    while !stack.is_empty() || node.is_some() {
        while let Some(current) = node {
            node = current.borrow().left.clone();
            stack.push(current);
        }
        let current = stack
            .pop()
            .expect("the loop condition leaves a node to visit");
        let current = current.borrow();
        if previous.is_some_and(|previous| current.val <= previous) {
            return false;
        }
        previous = Some(current.val);
        node = current.right.clone();
    }
    true
}
