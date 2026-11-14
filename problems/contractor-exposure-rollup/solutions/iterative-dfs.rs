use std::collections::{HashMap, HashSet};

use rust_decimal::Decimal;

/// One contractor on the explicit stack, with the index of the next child to look at.
struct Frame<'a> {
    node: &'a str,
    next: usize,
}

pub fn total_exposure(
    edges: Vec<Vec<String>>,
    contractors: Vec<String>,
    exposures: Vec<Decimal>,
    root: String,
) -> Decimal {
    let mut children: HashMap<&str, Vec<&str>> = HashMap::new();
    for edge in &edges {
        children
            .entry(edge[0].as_str())
            .or_default()
            .push(edge[1].as_str());
    }
    let own: HashMap<&str, Decimal> = contractors
        .iter()
        .map(String::as_str)
        .zip(exposures)
        .collect();
    let exposure_of = |name: &str| own.get(name).copied().unwrap_or(Decimal::ZERO);
    let root = root.as_str();
    let mut on_path = HashSet::from([root]); // meeting one again closes a cycle
    let mut finished = HashSet::new(); // fully explored contractors, already counted
    let mut total = exposure_of(root);
    let mut stack = vec![Frame {
        node: root,
        next: 0,
    }];
    while let Some(frame) = stack.last_mut() {
        let below = children.get(frame.node).map_or(&[][..], Vec::as_slice);
        if frame.next == below.len() {
            let node = frame.node;
            stack.pop();
            on_path.remove(node);
            finished.insert(node);
            continue;
        }
        let child = below[frame.next];
        frame.next += 1;
        if on_path.contains(child) {
            return Decimal::NEGATIVE_ONE;
        }
        if !finished.contains(child) {
            on_path.insert(child);
            total += exposure_of(child);
            stack.push(Frame {
                node: child,
                next: 0,
            });
        }
    }
    total
}
