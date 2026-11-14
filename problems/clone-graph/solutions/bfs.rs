use std::cell::RefCell;
use std::collections::{HashMap, VecDeque};
use std::rc::Rc;

use cs_support::GraphNode;

type Node = Rc<RefCell<GraphNode>>;
/// The copies, keyed by the address of the original node: identity, not value.
type Clones = HashMap<*const RefCell<GraphNode>, Node>;

fn new_clone(original: &Node) -> Node {
    Rc::new(RefCell::new(GraphNode::new(original.borrow().val)))
}

pub fn clone_graph(node: Option<Rc<RefCell<GraphNode>>>) -> Option<Rc<RefCell<GraphNode>>> {
    let node = node?;
    let root = new_clone(&node);
    let mut clones = Clones::from([(Rc::as_ptr(&node), Rc::clone(&root))]);
    let mut queue = VecDeque::from([node]);
    while let Some(original) = queue.pop_front() {
        let clone = Rc::clone(&clones[&Rc::as_ptr(&original)]);
        for neighbor in &original.borrow().neighbors {
            let neighbor_clone = match clones.get(&Rc::as_ptr(neighbor)) {
                Some(existing) => Rc::clone(existing),
                None => {
                    let created = new_clone(neighbor);
                    clones.insert(Rc::as_ptr(neighbor), Rc::clone(&created));
                    queue.push_back(Rc::clone(neighbor));
                    created
                }
            };
            clone.borrow_mut().neighbors.push(neighbor_clone);
        }
    }
    Some(root)
}
