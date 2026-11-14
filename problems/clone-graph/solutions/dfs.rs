use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

use cs_support::GraphNode;

type Node = Rc<RefCell<GraphNode>>;
/// The copies, keyed by the address of the original node: identity, not value.
type Clones = HashMap<*const RefCell<GraphNode>, Node>;

pub fn clone_graph(node: Option<Rc<RefCell<GraphNode>>>) -> Option<Rc<RefCell<GraphNode>>> {
    let node = node?;
    Some(copy(&node, &mut Clones::new()))
}

fn copy(original: &Node, clones: &mut Clones) -> Node {
    if let Some(clone) = clones.get(&Rc::as_ptr(original)) {
        return Rc::clone(clone);
    }
    // Register the copy before visiting neighbors: a cycle leads back here and must find this
    // copy instead of starting a second one.
    let clone = Rc::new(RefCell::new(GraphNode::new(original.borrow().val)));
    clones.insert(Rc::as_ptr(original), Rc::clone(&clone));
    let neighbors: Vec<Node> = original
        .borrow()
        .neighbors
        .iter()
        .map(|neighbor| copy(neighbor, clones))
        .collect();
    clone.borrow_mut().neighbors = neighbors;
    clone
}
