use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn is_subtree(
    root: Option<Rc<RefCell<TreeNode>>>,
    sub_root: Option<Rc<RefCell<TreeNode>>>,
) -> bool {
    contains(&root, &sub_root)
}

fn contains(
    root: &Option<Rc<RefCell<TreeNode>>>,
    sub_root: &Option<Rc<RefCell<TreeNode>>>,
) -> bool {
    let Some(node) = root else { return false };
    let node = node.borrow();
    same(root, sub_root) || contains(&node.left, sub_root) || contains(&node.right, sub_root)
}

fn same(a: &Option<Rc<RefCell<TreeNode>>>, b: &Option<Rc<RefCell<TreeNode>>>) -> bool {
    match (a, b) {
        (None, None) => true,
        (Some(a), Some(b)) => {
            let (a, b) = (a.borrow(), b.borrow());
            a.val == b.val && same(&a.left, &b.left) && same(&a.right, &b.right)
        }
        _ => false,
    }
}
