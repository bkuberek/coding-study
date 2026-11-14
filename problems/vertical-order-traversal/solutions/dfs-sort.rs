use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn vertical_order(root: Option<Rc<RefCell<TreeNode>>>) -> Vec<Vec<i32>> {
    let mut entries = Vec::new(); // (column, row, value) in pre-order
    visit(&root, 0, 0, &mut entries);
    // `sort_by_key` is stable, so pre-order (left to right) survives among nodes with the same
    // column and row.
    entries.sort_by_key(|&(column, row, _)| (column, row));
    entries
        .chunk_by(|a, b| a.0 == b.0)
        .map(|group| group.iter().map(|&(_, _, value)| value).collect())
        .collect()
}

fn visit(
    node: &Option<Rc<RefCell<TreeNode>>>,
    column: i32,
    row: i32,
    entries: &mut Vec<(i32, i32, i32)>,
) {
    if let Some(node) = node {
        let node = node.borrow();
        entries.push((column, row, node.val));
        visit(&node.left, column - 1, row + 1, entries);
        visit(&node.right, column + 1, row + 1, entries);
    }
}
