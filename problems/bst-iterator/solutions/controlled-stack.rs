use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub struct BSTIterator {
    /// Nodes whose left subtree is finished (or about to be) and that are not returned yet.
    stack: Vec<Rc<RefCell<TreeNode>>>,
}

impl BSTIterator {
    pub fn new(root: Option<Rc<RefCell<TreeNode>>>) -> Self {
        let mut iterator = BSTIterator { stack: Vec::new() };
        iterator.push_left_spine(root);
        iterator
    }

    fn push_left_spine(&mut self, mut node: Option<Rc<RefCell<TreeNode>>>) {
        while let Some(current) = node {
            node = current.borrow().left.clone();
            self.stack.push(current);
        }
    }

    #[allow(clippy::should_implement_trait)]
    pub fn next(&mut self) -> i32 {
        let node = self
            .stack
            .pop()
            .expect("next is only called while has_next holds");
        let node = node.borrow();
        self.push_left_spine(node.right.clone());
        node.val
    }

    pub fn has_next(&mut self) -> bool {
        !self.stack.is_empty()
    }
}
