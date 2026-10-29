use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn right_side_view(root: Option<Rc<RefCell<TreeNode>>>) -> Vec<i32> {
    let mut view = Vec::new();
    visit(&root, 0, &mut view);
    view
}

fn visit(node: &Option<Rc<RefCell<TreeNode>>>, depth: usize, view: &mut Vec<i32>) {
    let Some(node) = node else { return };
    let node = node.borrow();
    if depth == view.len() {
        view.push(node.val);
    }
    visit(&node.right, depth + 1, view);
    visit(&node.left, depth + 1, view);
}
