use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn pick_tree_node(
    root: Option<Rc<RefCell<TreeNode>>>,
    node: Option<Rc<RefCell<TreeNode>>>,
) -> Option<Rc<RefCell<TreeNode>>> {
    node
}
