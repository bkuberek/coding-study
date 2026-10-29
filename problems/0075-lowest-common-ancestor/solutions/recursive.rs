use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn lowest_common_ancestor(
    root: Option<Rc<RefCell<TreeNode>>>,
    p: Option<Rc<RefCell<TreeNode>>>,
    q: Option<Rc<RefCell<TreeNode>>>,
) -> Option<Rc<RefCell<TreeNode>>> {
    find(&root, &p, &q)
}

/// The answer if both `p` and `q` are below `root`, else whichever of them is below, else
/// `None`. Two nodes are the same node when their `Rc`s point at the same allocation.
fn find(
    root: &Option<Rc<RefCell<TreeNode>>>,
    p: &Option<Rc<RefCell<TreeNode>>>,
    q: &Option<Rc<RefCell<TreeNode>>>,
) -> Option<Rc<RefCell<TreeNode>>> {
    let node = root.as_ref()?;
    if is_node(node, p) || is_node(node, q) {
        return root.clone();
    }
    let (left, right) = {
        let node = node.borrow();
        (find(&node.left, p, q), find(&node.right, p, q))
    };
    if left.is_some() && right.is_some() {
        return root.clone();
    }
    left.or(right)
}

fn is_node(node: &Rc<RefCell<TreeNode>>, target: &Option<Rc<RefCell<TreeNode>>>) -> bool {
    target
        .as_ref()
        .is_some_and(|target| Rc::ptr_eq(node, target))
}
