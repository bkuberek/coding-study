use std::cell::RefCell;
use std::collections::{HashMap, HashSet};
use std::rc::Rc;

use cs_support::TreeNode;

/// A node's identity: the address of its allocation. `Rc<RefCell<_>>` does not implement
/// `Hash`, and two nodes with equal values must stay different keys.
type Id = *const RefCell<TreeNode>;

pub fn lowest_common_ancestor(
    root: Option<Rc<RefCell<TreeNode>>>,
    p: Option<Rc<RefCell<TreeNode>>>,
    q: Option<Rc<RefCell<TreeNode>>>,
) -> Option<Rc<RefCell<TreeNode>>> {
    let (Some(root), Some(p), Some(q)) = (root, p, q) else {
        return None;
    };
    let mut parent: HashMap<Id, Option<Rc<RefCell<TreeNode>>>> =
        HashMap::from([(Rc::as_ptr(&root), None)]);
    let mut pending = vec![root];
    while !parent.contains_key(&Rc::as_ptr(&p)) || !parent.contains_key(&Rc::as_ptr(&q)) {
        let current = pending.pop().expect("p and q are nodes of the tree");
        let node = current.borrow();
        for child in [&node.left, &node.right].into_iter().flatten() {
            parent.insert(Rc::as_ptr(child), Some(Rc::clone(&current)));
            pending.push(Rc::clone(child));
        }
    }
    let mut ancestors_of_p: HashSet<Id> = HashSet::new();
    let mut node = Some(p);
    while let Some(current) = node {
        ancestors_of_p.insert(Rc::as_ptr(&current));
        node = parent[&Rc::as_ptr(&current)].clone();
    }
    let mut node = q;
    while !ancestors_of_p.contains(&Rc::as_ptr(&node)) {
        node = parent[&Rc::as_ptr(&node)]
            .clone()
            .expect("q is below the root, so an ancestor of it is in the set");
    }
    Some(node)
}
