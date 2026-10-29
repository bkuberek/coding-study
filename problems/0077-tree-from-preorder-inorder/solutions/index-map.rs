use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn build_tree(preorder: Vec<i32>, inorder: Vec<i32>) -> Option<Rc<RefCell<TreeNode>>> {
    let position: HashMap<i32, usize> = inorder
        .iter()
        .enumerate()
        .map(|(index, &value)| (value, index))
        .collect();
    let mut next_root = 0;
    build(&preorder, &position, &mut next_root, 0, inorder.len())
}

/// Tree whose in-order walk is `inorder[low..high]`; its root is the next pre-order value.
fn build(
    preorder: &[i32],
    position: &HashMap<i32, usize>,
    next_root: &mut usize,
    low: usize,
    high: usize,
) -> Option<Rc<RefCell<TreeNode>>> {
    if low == high {
        return None;
    }
    let value = preorder[*next_root];
    *next_root += 1;
    let split = position[&value];
    let mut node = TreeNode::new(value);
    node.left = build(preorder, position, next_root, low, split);
    node.right = build(preorder, position, next_root, split + 1, high);
    Some(Rc::new(RefCell::new(node)))
}
