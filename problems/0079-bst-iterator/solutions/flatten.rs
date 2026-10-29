use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub struct BSTIterator {
    values: Vec<i32>,
    position: usize,
}

impl BSTIterator {
    pub fn new(root: Option<Rc<RefCell<TreeNode>>>) -> Self {
        let mut values = Vec::new();
        collect(&root, &mut values);
        BSTIterator {
            values,
            position: 0,
        }
    }

    #[allow(clippy::should_implement_trait)]
    pub fn next(&mut self) -> i32 {
        let value = self.values[self.position];
        self.position += 1;
        value
    }

    pub fn has_next(&mut self) -> bool {
        self.position < self.values.len()
    }
}

fn collect(node: &Option<Rc<RefCell<TreeNode>>>, values: &mut Vec<i32>) {
    if let Some(node) = node {
        let node = node.borrow();
        collect(&node.left, values);
        values.push(node.val);
        collect(&node.right, values);
    }
}
