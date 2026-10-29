//! Linked structures, their JSON encodings and the node modifiers
//! (docs/specs/problem-format.md#serialization-of-linked-structures,
//! docs/specs/runners.md#node-modifiers).
//!
//! Identity compares node addresses: the `Box` of a list node, the `Rc` of a tree or graph node.
//! The bridge takes a parameter's addresses before the call and runs the call under
//! [`crate::retaining`], so no memory freed during the call can come back as a new node at an
//! address the parameter held. A `Box` list has one owner, so `ref_of` and `as: index` cannot
//! name its nodes: the CLI generates no bridge for them, and a cyclic list input is an error.

use std::cell::RefCell;
use std::collections::{HashMap, HashSet, VecDeque};
use std::rc::Rc;

use cs_support::{GraphNode, ListNode, TreeNode};

use crate::codec::{mismatch, Decode, Encode};
use crate::json::Json;

/// Longer output lists are reported as too long.
const MAX_LIST_NODES: usize = 100_000;
/// How `as: index` encodes a `None` result.
const NULL_INDEX: i64 = -1;

pub type List = Option<Box<ListNode>>;
pub type Tree = Option<Rc<RefCell<TreeNode>>>;
pub type Graph = Option<Rc<RefCell<GraphNode>>>;

fn node_value(value: &Json) -> Result<i32, String> {
    value
        .as_i64()
        .and_then(|number| i32::try_from(number).ok())
        .ok_or_else(|| format!("node value must be an int, got {}", value.text()))
}

impl Decode for List {
    /// `[1, 2, 3]`. The cyclic encoding `{"values": [...], "cycle_at": k}` cannot be built.
    fn decode(value: &Json) -> Result<Self, String> {
        let Some(values) = value.as_array() else {
            if value.get("values").is_some() && value.get("cycle_at").is_some() {
                return Err(
                    "a cyclic list cannot be built in Rust: an Option<Box<ListNode>> has one \
                     owner per node, so no node can point back"
                        .into(),
                );
            }
            return Err(format!("not a ListNode encoding: {}", value.text()));
        };
        let mut head = None;
        for item in values.iter().rev() {
            head = Some(Box::new(ListNode {
                val: node_value(item)?,
                next: head,
            }));
        }
        Ok(head)
    }

    fn name() -> String {
        "ListNode".into()
    }
}

impl Decode for Tree {
    /// Level order with `null` for missing children.
    fn decode(value: &Json) -> Result<Self, String> {
        let values = value.as_array().ok_or_else(|| mismatch::<Self>(value))?;
        let Some(first) = values.first().filter(|first| **first != Json::Null) else {
            return Ok(None);
        };
        let root = Rc::new(RefCell::new(TreeNode::new(node_value(first)?)));
        let mut parents = VecDeque::from([Rc::clone(&root)]);
        let mut children = values[1..].iter();
        let mut child = || -> Result<Tree, String> {
            match children.next() {
                None | Some(Json::Null) => Ok(None),
                Some(item) => Ok(Some(Rc::new(RefCell::new(TreeNode::new(node_value(
                    item,
                )?))))),
            }
        };
        while let Some(parent) = parents.pop_front() {
            let (left, right) = (child()?, child()?);
            parents.extend(left.iter().chain(right.iter()).cloned());
            let mut parent = parent.borrow_mut();
            parent.left = left;
            parent.right = right;
        }
        Ok(Some(root))
    }

    fn name() -> String {
        "TreeNode".into()
    }
}

impl Decode for Graph {
    /// A 1-indexed adjacency list where node `i` has value `i`; the result is node 1.
    fn decode(value: &Json) -> Result<Self, String> {
        let adjacency = value.as_array().ok_or_else(|| mismatch::<Self>(value))?;
        let count = adjacency.len();
        let nodes: Vec<Rc<RefCell<GraphNode>>> = (1..=count)
            .map(|val| Rc::new(RefCell::new(GraphNode::new(val as i32))))
            .collect();
        for (index, entry) in adjacency.iter().enumerate() {
            let neighbors = entry.as_array().ok_or_else(|| {
                format!(
                    "expected an array for the neighbors of graph node {}, got {}",
                    index + 1,
                    entry.text()
                )
            })?;
            for neighbor in neighbors {
                let position = neighbor
                    .as_i64()
                    .filter(|value| (1..=count as i64).contains(value))
                    .ok_or_else(|| {
                        format!(
                            "graph neighbor {} is not a node value 1..{count}",
                            neighbor.text()
                        )
                    })?;
                let target = Rc::clone(&nodes[position as usize - 1]);
                nodes[index].borrow_mut().neighbors.push(target);
            }
        }
        Ok(nodes.into_iter().next())
    }

    fn name() -> String {
        "GraphNode".into()
    }
}

impl Encode for List {
    fn encode(&self) -> Result<Json, String> {
        let mut values = Vec::new();
        let mut node = self.as_deref();
        while let Some(current) = node {
            if values.len() == MAX_LIST_NODES {
                return Err("list too long".into());
            }
            values.push(Json::Int(i64::from(current.val)));
            node = current.next.as_deref();
        }
        Ok(Json::Array(values))
    }
}

impl Encode for Tree {
    /// Level order with `null` for missing children, trailing nulls trimmed.
    fn encode(&self) -> Result<Json, String> {
        let mut values = Vec::new();
        let mut seen = HashSet::new();
        let mut pending = VecDeque::from([self.clone()]);
        while let Some(node) = pending.pop_front() {
            let Some(node) = node else {
                values.push(Json::Null);
                continue;
            };
            if !seen.insert(Rc::as_ptr(&node)) {
                return Err("tree contains a cycle or a shared node".into());
            }
            let node = node.borrow();
            values.push(Json::Int(i64::from(node.val)));
            pending.push_back(node.left.clone());
            pending.push_back(node.right.clone());
        }
        while values.last() == Some(&Json::Null) {
            values.pop();
        }
        Ok(Json::Array(values))
    }
}

impl Encode for Graph {
    /// The neighbor values of nodes 1..k, where k nodes are reachable from the given one.
    fn encode(&self) -> Result<Json, String> {
        let mut by_value: HashMap<i32, Rc<RefCell<GraphNode>>> = HashMap::new();
        for node in graph_order(self) {
            let val = node.borrow().val;
            if by_value.insert(val, node).is_some() {
                return Err(format!("graph has two nodes with value {val}"));
            }
        }
        let mut adjacency = Vec::with_capacity(by_value.len());
        for val in 1..=by_value.len() as i32 {
            let node = by_value.get(&val).ok_or_else(|| {
                "graph node values must be exactly 1..k for k reachable nodes".to_string()
            })?;
            let neighbors = node
                .borrow()
                .neighbors
                .iter()
                .map(|neighbor| Json::Int(i64::from(neighbor.borrow().val)))
                .collect();
            adjacency.push(Json::Array(neighbors));
        }
        Ok(Json::Array(adjacency))
    }
}

/// Breadth-first from `start`, neighbors in adjacency order, each node once.
fn graph_order(start: &Graph) -> Vec<Rc<RefCell<GraphNode>>> {
    let mut order = Vec::new();
    let mut seen = HashSet::new();
    let mut pending: VecDeque<Rc<RefCell<GraphNode>>> = start.iter().cloned().collect();
    while let Some(node) = pending.pop_front() {
        if !seen.insert(Rc::as_ptr(&node)) {
            continue;
        }
        pending.extend(node.borrow().neighbors.iter().cloned());
        order.push(node);
    }
    order
}

/// Level order, left before right, each node once.
fn tree_order(root: &Tree) -> Vec<Rc<RefCell<TreeNode>>> {
    let mut order = Vec::new();
    let mut seen = HashSet::new();
    let mut pending: VecDeque<Rc<RefCell<TreeNode>>> = root.iter().cloned().collect();
    while let Some(node) = pending.pop_front() {
        if !seen.insert(Rc::as_ptr(&node)) {
            continue;
        }
        let children = node.borrow();
        pending.extend(children.left.iter().chain(children.right.iter()).cloned());
        drop(children);
        order.push(node);
    }
    order
}

/// A value holding nodes: a list, a tree, a graph, or a vector of them.
pub trait Nodes {
    /// The address of every node reachable from the value, in traversal order
    /// (docs/specs/runners.md#node-modifiers); a vector concatenates its elements'.
    fn addresses(&self) -> Vec<usize>;
}

impl Nodes for List {
    fn addresses(&self) -> Vec<usize> {
        let mut addresses = Vec::new();
        let mut node = self.as_deref();
        while let Some(current) = node {
            addresses.push(current as *const ListNode as usize);
            node = current.next.as_deref();
        }
        addresses
    }
}

impl Nodes for Tree {
    fn addresses(&self) -> Vec<usize> {
        tree_order(self)
            .iter()
            .map(|node| Rc::as_ptr(node) as usize)
            .collect()
    }
}

impl Nodes for Graph {
    fn addresses(&self) -> Vec<usize> {
        graph_order(self)
            .iter()
            .map(|node| Rc::as_ptr(node) as usize)
            .collect()
    }
}

impl<T: Nodes> Nodes for Vec<T> {
    fn addresses(&self) -> Vec<usize> {
        self.iter().flat_map(Nodes::addresses).collect()
    }
}

/// The nodes a parameter held before the call, in traversal order.
pub struct Identity(Vec<usize>);

impl Identity {
    pub fn of<T: Nodes>(value: &T) -> Self {
        Identity(value.addresses())
    }
}

/// A value whose nodes are shared, so `ref_of` can hand out one of them: a tree, a graph, or a
/// vector of them.
pub trait Shared {
    type Node;

    /// The first node in traversal order whose `val` is `val`.
    fn node_with_value(&self, val: i32) -> Option<Rc<RefCell<Self::Node>>>;
}

impl Shared for Tree {
    type Node = TreeNode;

    fn node_with_value(&self, val: i32) -> Option<Rc<RefCell<TreeNode>>> {
        tree_order(self)
            .into_iter()
            .find(|node| node.borrow().val == val)
    }
}

impl Shared for Graph {
    type Node = GraphNode;

    fn node_with_value(&self, val: i32) -> Option<Rc<RefCell<GraphNode>>> {
        graph_order(self)
            .into_iter()
            .find(|node| node.borrow().val == val)
    }
}

impl<T: Shared> Shared for Vec<T> {
    type Node = T::Node;

    fn node_with_value(&self, val: i32) -> Option<Rc<RefCell<T::Node>>> {
        self.iter().find_map(|value| value.node_with_value(val))
    }
}

/// `ref_of`: the node of `within` whose value is the JSON value, or `None` for `null`.
pub(crate) fn node_of<S: Shared>(
    value: &Json,
    within: &S,
    of: &str,
) -> Result<Option<Rc<RefCell<S::Node>>>, String> {
    if *value == Json::Null {
        return Ok(None);
    }
    let val = node_value(value)?;
    within
        .node_with_value(val)
        .map(Some)
        .ok_or_else(|| format!("no node with value {val} in \"{of}\""))
}

/// One node or none: what a function returns `as: value` or `as: index`.
pub trait Single {
    fn value(&self) -> Option<i32>;
    fn address(&self) -> Option<usize>;
}

impl Single for List {
    fn value(&self) -> Option<i32> {
        self.as_ref().map(|node| node.val)
    }

    fn address(&self) -> Option<usize> {
        self.as_deref().map(|node| node as *const ListNode as usize)
    }
}

impl Single for Tree {
    fn value(&self) -> Option<i32> {
        self.as_ref().map(|node| node.borrow().val)
    }

    fn address(&self) -> Option<usize> {
        self.as_ref().map(|node| Rc::as_ptr(node) as usize)
    }
}

impl Single for Graph {
    fn value(&self) -> Option<i32> {
        self.as_ref().map(|node| node.borrow().val)
    }

    fn address(&self) -> Option<usize> {
        self.as_ref().map(|node| Rc::as_ptr(node) as usize)
    }
}

/// `as: value`: the returned node's `val`, or `null`.
pub struct ValueOf<T>(pub T);

impl<T: Single> Encode for ValueOf<T> {
    fn encode(&self) -> Result<Json, String> {
        Ok(self
            .0
            .value()
            .map_or(Json::Null, |val| Json::Int(i64::from(val))))
    }
}

/// `as: index`, `of: <param>`: the returned node's position in the parameter's traversal order,
/// `-1` for `None`.
pub struct IndexIn<T> {
    node: T,
    among: Identity,
    of: &'static str,
}

impl<T> IndexIn<T> {
    pub fn new(node: T, among: Identity, of: &'static str) -> Self {
        IndexIn { node, among, of }
    }
}

impl<T: Single> Encode for IndexIn<T> {
    fn encode(&self) -> Result<Json, String> {
        let Some(address) = self.node.address() else {
            return Ok(Json::Int(NULL_INDEX));
        };
        self.among
            .0
            .iter()
            .position(|candidate| *candidate == address)
            .map(|index| Json::Int(index as i64))
            .ok_or_else(|| format!("the returned node is not a node of \"{}\"", self.of))
    }
}

/// `no_alias_with: <param>`: the returned structure, which must not reuse a node of the
/// parameter.
pub struct NoAlias<T> {
    value: T,
    inputs: Identity,
    with: &'static str,
}

impl<T> NoAlias<T> {
    pub fn new(value: T, inputs: Identity, with: &'static str) -> Self {
        NoAlias {
            value,
            inputs,
            with,
        }
    }
}

impl<T: Encode + Nodes> Encode for NoAlias<T> {
    fn encode(&self) -> Result<Json, String> {
        let encoded = self.value.encode()?;
        let inputs: HashSet<usize> = self.inputs.0.iter().copied().collect();
        if self
            .value
            .addresses()
            .iter()
            .any(|address| inputs.contains(address))
        {
            return Err(format!(
                "the returned structure shares nodes with \"{}\"",
                self.with
            ));
        }
        Ok(encoded)
    }
}

#[cfg(test)]
mod tests {
    use super::{node_of, Graph, Identity, IndexIn, List, NoAlias, Tree, ValueOf};
    use crate::codec::{Decode, Encode};
    use crate::json::Json;
    use std::rc::Rc;

    fn parsed(text: &str) -> Json {
        Json::parse(text).unwrap()
    }

    fn round_trip<T: Decode + Encode>(text: &str) -> String {
        T::decode(&parsed(text)).unwrap().encode().unwrap().text()
    }

    #[test]
    fn lists_round_trip() {
        assert_eq!(round_trip::<List>("[1,2,3]"), "[1,2,3]");
        assert_eq!(round_trip::<List>("[]"), "[]");
    }

    #[test]
    fn a_cyclic_list_cannot_be_built() {
        let error = List::decode(&parsed(r#"{"values": [1, 2], "cycle_at": 0}"#)).unwrap_err();
        assert!(
            error.starts_with("a cyclic list cannot be built in Rust"),
            "{error}"
        );
    }

    #[test]
    fn trees_round_trip_with_trailing_nulls_trimmed() {
        assert_eq!(
            round_trip::<Tree>("[1,null,2,3,null,null,null]"),
            "[1,null,2,3]"
        );
        assert_eq!(round_trip::<Tree>("[]"), "[]");
        assert_eq!(round_trip::<Tree>("[null]"), "[]");
    }

    #[test]
    fn a_shared_tree_node_is_invalid_output() {
        let tree = Tree::decode(&parsed("[1,2]")).unwrap();
        let root = tree.clone().unwrap();
        let left = root.borrow().left.clone();
        root.borrow_mut().right = left;
        assert_eq!(
            tree.encode(),
            Err("tree contains a cycle or a shared node".into())
        );
    }

    #[test]
    fn graphs_round_trip() {
        assert_eq!(
            round_trip::<Graph>("[[2,4],[1,3],[2,4],[1,3]]"),
            "[[2,4],[1,3],[2,4],[1,3]]"
        );
        assert_eq!(round_trip::<Graph>("[]"), "[]");
    }

    #[test]
    fn graph_neighbors_must_name_nodes() {
        assert!(Graph::decode(&parsed("[[3]]")).is_err());
    }

    #[test]
    fn ref_of_finds_the_first_node_in_level_order() {
        let tree = Tree::decode(&parsed("[5,3,3]")).unwrap();
        let node = node_of(&parsed("3"), &tree, "root").unwrap().unwrap();
        let left = tree.as_ref().unwrap().borrow().left.clone().unwrap();
        assert!(Rc::ptr_eq(&node, &left));
        assert_eq!(node_of(&parsed("null"), &tree, "root").unwrap(), None);
        assert_eq!(
            node_of(&parsed("9"), &tree, "root").unwrap_err(),
            "no node with value 9 in \"root\""
        );
    }

    #[test]
    fn index_in_finds_the_returned_node() {
        let tree = Tree::decode(&parsed("[5,6,7]")).unwrap();
        let right = tree.as_ref().unwrap().borrow().right.clone();
        let identity = Identity::of(&tree);
        assert_eq!(
            IndexIn::new(right, identity, "root").encode(),
            Ok(Json::Int(2))
        );
        let none: Tree = None;
        let empty = IndexIn::new(none, Identity::of(&tree), "root");
        assert_eq!(empty.encode(), Ok(Json::Int(-1)));
    }

    #[test]
    fn index_in_rejects_a_new_node() {
        let tree = Tree::decode(&parsed("[5]")).unwrap();
        let other = Tree::decode(&parsed("[5]")).unwrap();
        assert_eq!(
            IndexIn::new(other, Identity::of(&tree), "root").encode(),
            Err("the returned node is not a node of \"root\"".into())
        );
    }

    #[test]
    fn value_of_is_the_node_value_or_null() {
        let list = List::decode(&parsed("[4]")).unwrap();
        assert_eq!(ValueOf(list).encode(), Ok(Json::Int(4)));
        let empty: Tree = None;
        assert_eq!(ValueOf(empty).encode(), Ok(Json::Null));
    }

    #[test]
    fn no_alias_rejects_returning_the_input_list() {
        let list = List::decode(&parsed("[1,2]")).unwrap();
        let identity = Identity::of(&list);
        assert!(NoAlias::new(list, identity, "head").encode().is_err());
    }

    #[test]
    fn no_alias_accepts_a_copy() {
        let list = List::decode(&parsed("[1,2]")).unwrap();
        let copy = list.clone();
        let encoded = NoAlias::new(copy, Identity::of(&list), "head").encode();
        assert_eq!(encoded, Ok(parsed("[1,2]")));
    }
}
