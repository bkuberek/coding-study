use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn build_tree(preorder: Vec<i32>, inorder: Vec<i32>) -> Option<Rc<RefCell<TreeNode>>> {
    build(&preorder, &inorder)
}

/// Tree whose pre-order walk is `preorder` and in-order walk is `inorder` (same length).
/// Slices are the windows, so no index arithmetic is needed.
fn build(preorder: &[i32], inorder: &[i32]) -> Option<Rc<RefCell<TreeNode>>> {
    let (&value, preorder_rest) = preorder.split_first()?;
    // The root's position inside this window of inorder: a linear scan.
    let split = inorder.iter().position(|&other| other == value)?;
    let mut node = TreeNode::new(value);
    node.left = build(&preorder_rest[..split], &inorder[..split]);
    node.right = build(&preorder_rest[split..], &inorder[split + 1..]);
    Some(Rc::new(RefCell::new(node)))
}
