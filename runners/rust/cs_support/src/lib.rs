//! Node types shared by solutions and the runner
//! (docs/specs/problem-format.md#go-and-rust-mapping).
//!
//! `ListNode` and `TreeNode` are LeetCode's Rust definitions, so a LeetCode solution compiles
//! unchanged: a list is `Option<Box<ListNode>>` and a tree `Option<Rc<RefCell<TreeNode>>>`, with
//! `None` for the empty one. A graph is `Option<Rc<RefCell<GraphNode>>>`.

use std::cell::RefCell;
use std::fmt;
use std::rc::Rc;

/// A singly linked list node. A `Box` has one owner, so a list can neither be cyclic nor share
/// a tail with another list.
#[derive(PartialEq, Eq, Clone, Debug)]
pub struct ListNode {
    pub val: i32,
    pub next: Option<Box<ListNode>>,
}

impl ListNode {
    #[inline]
    pub fn new(val: i32) -> Self {
        ListNode { next: None, val }
    }
}

/// A binary tree node.
#[derive(Debug, PartialEq, Eq)]
pub struct TreeNode {
    pub val: i32,
    pub left: Option<Rc<RefCell<TreeNode>>>,
    pub right: Option<Rc<RefCell<TreeNode>>>,
}

impl TreeNode {
    #[inline]
    pub fn new(val: i32) -> Self {
        TreeNode {
            val,
            left: None,
            right: None,
        }
    }
}

/// A graph node with its neighbors in adjacency order. A graph may have cycles, so `GraphNode`
/// neither compares nor prints its neighbors recursively: `Debug` shows their values.
pub struct GraphNode {
    pub val: i32,
    pub neighbors: Vec<Rc<RefCell<GraphNode>>>,
}

impl GraphNode {
    #[inline]
    pub fn new(val: i32) -> Self {
        GraphNode {
            val,
            neighbors: Vec::new(),
        }
    }
}

impl fmt::Debug for GraphNode {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        let neighbors: Vec<Option<i32>> = self
            .neighbors
            .iter()
            .map(|neighbor| neighbor.try_borrow().ok().map(|node| node.val))
            .collect();
        formatter
            .debug_struct("GraphNode")
            .field("val", &self.val)
            .field("neighbors", &neighbors)
            .finish()
    }
}

#[cfg(test)]
mod tests {
    use super::{GraphNode, ListNode, TreeNode};
    use std::cell::RefCell;
    use std::rc::Rc;

    #[test]
    fn new_nodes_have_no_links() {
        assert_eq!(ListNode::new(1).next, None);
        let tree = TreeNode::new(2);
        assert_eq!((tree.left, tree.right), (None, None));
        assert!(GraphNode::new(3).neighbors.is_empty());
    }

    #[test]
    fn a_cyclic_graph_prints_neighbor_values() {
        let one = Rc::new(RefCell::new(GraphNode::new(1)));
        let two = Rc::new(RefCell::new(GraphNode::new(2)));
        one.borrow_mut().neighbors.push(Rc::clone(&two));
        two.borrow_mut().neighbors.push(Rc::clone(&one));
        assert_eq!(
            format!("{:?}", one.borrow()),
            "GraphNode { val: 1, neighbors: [Some(2)] }"
        );
    }
}
