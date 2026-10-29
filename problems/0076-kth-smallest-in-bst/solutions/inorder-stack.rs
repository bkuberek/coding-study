use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn kth_smallest(root: Option<Rc<RefCell<TreeNode>>>, mut k: i32) -> i32 {
    let mut stack: Vec<Rc<RefCell<TreeNode>>> = Vec::new();
    let mut node = root;
    loop {
        while let Some(current) = node {
            node = current.borrow().left.clone();
            stack.push(current);
        }
        let current = stack.pop().expect("k is at most the number of nodes");
        k -= 1;
        if k == 0 {
            return current.borrow().val;
        }
        node = current.borrow().right.clone();
    }
}
