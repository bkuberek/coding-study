use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn is_same_tree(p: Option<Rc<RefCell<TreeNode>>>, q: Option<Rc<RefCell<TreeNode>>>) -> bool {
    same(&p, &q)
}

fn same(p: &Option<Rc<RefCell<TreeNode>>>, q: &Option<Rc<RefCell<TreeNode>>>) -> bool {
    match (p, q) {
        (None, None) => true,
        (Some(a), Some(b)) => {
            let (a, b) = (a.borrow(), b.borrow());
            a.val == b.val && same(&a.left, &b.left) && same(&a.right, &b.right)
        }
        _ => false,
    }
}
