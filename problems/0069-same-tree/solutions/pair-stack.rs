use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn is_same_tree(p: Option<Rc<RefCell<TreeNode>>>, q: Option<Rc<RefCell<TreeNode>>>) -> bool {
    let mut pending = vec![(p, q)];
    while let Some(pair) = pending.pop() {
        match pair {
            (None, None) => {}
            (Some(a), Some(b)) => {
                let (a, b) = (a.borrow(), b.borrow());
                if a.val != b.val {
                    return false;
                }
                pending.push((a.right.clone(), b.right.clone()));
                pending.push((a.left.clone(), b.left.clone()));
            }
            _ => return false,
        }
    }
    true
}
