// Conformance reference: every echo method returns its argument unchanged.

use std::cell::RefCell;
use std::rc::Rc;

use cs_support::{GraphNode, ListNode, TreeNode};

pub struct TypeEcho {}

impl TypeEcho {
    pub fn new(label: String) -> Self {
        TypeEcho {}
    }

    pub fn echo_int(&mut self, value: i32) -> i32 {
        value
    }

    pub fn echo_long(&mut self, value: i64) -> i64 {
        value
    }

    pub fn echo_double(&mut self, value: f64) -> f64 {
        value
    }

    pub fn echo_bool(&mut self, value: bool) -> bool {
        value
    }

    pub fn echo_string(&mut self, value: String) -> String {
        value
    }

    pub fn echo_char(&mut self, value: char) -> char {
        value
    }

    pub fn echo_int_array(&mut self, value: Vec<i32>) -> Vec<i32> {
        value
    }

    pub fn echo_long_array(&mut self, value: Vec<i64>) -> Vec<i64> {
        value
    }

    pub fn echo_double_array(&mut self, value: Vec<f64>) -> Vec<f64> {
        value
    }

    pub fn echo_bool_array(&mut self, value: Vec<bool>) -> Vec<bool> {
        value
    }

    pub fn echo_char_array(&mut self, value: Vec<char>) -> Vec<char> {
        value
    }

    pub fn echo_string_array(&mut self, value: Vec<String>) -> Vec<String> {
        value
    }

    pub fn echo_int_matrix(&mut self, value: Vec<Vec<i32>>) -> Vec<Vec<i32>> {
        value
    }

    pub fn echo_long_matrix(&mut self, value: Vec<Vec<i64>>) -> Vec<Vec<i64>> {
        value
    }

    pub fn echo_double_matrix(&mut self, value: Vec<Vec<f64>>) -> Vec<Vec<f64>> {
        value
    }

    pub fn echo_bool_matrix(&mut self, value: Vec<Vec<bool>>) -> Vec<Vec<bool>> {
        value
    }

    pub fn echo_char_matrix(&mut self, value: Vec<Vec<char>>) -> Vec<Vec<char>> {
        value
    }

    pub fn echo_string_matrix(&mut self, value: Vec<Vec<String>>) -> Vec<Vec<String>> {
        value
    }

    pub fn echo_int_list(&mut self, value: Vec<i32>) -> Vec<i32> {
        value
    }

    pub fn echo_long_list(&mut self, value: Vec<i64>) -> Vec<i64> {
        value
    }

    pub fn echo_double_list(&mut self, value: Vec<f64>) -> Vec<f64> {
        value
    }

    pub fn echo_bool_list(&mut self, value: Vec<bool>) -> Vec<bool> {
        value
    }

    pub fn echo_char_list(&mut self, value: Vec<char>) -> Vec<char> {
        value
    }

    pub fn echo_string_list(&mut self, value: Vec<String>) -> Vec<String> {
        value
    }

    pub fn echo_int_array_list(&mut self, value: Vec<Vec<i32>>) -> Vec<Vec<i32>> {
        value
    }

    pub fn echo_int_list_list(&mut self, value: Vec<Vec<i32>>) -> Vec<Vec<i32>> {
        value
    }

    pub fn echo_string_list_list(&mut self, value: Vec<Vec<String>>) -> Vec<Vec<String>> {
        value
    }

    pub fn echo_int_list_list_list(&mut self, value: Vec<Vec<Vec<i32>>>) -> Vec<Vec<Vec<i32>>> {
        value
    }

    pub fn echo_list_node(&mut self, value: Option<Box<ListNode>>) -> Option<Box<ListNode>> {
        value
    }

    pub fn echo_tree_node(
        &mut self,
        value: Option<Rc<RefCell<TreeNode>>>,
    ) -> Option<Rc<RefCell<TreeNode>>> {
        value
    }

    pub fn echo_graph_node(
        &mut self,
        value: Option<Rc<RefCell<GraphNode>>>,
    ) -> Option<Rc<RefCell<GraphNode>>> {
        value
    }

    pub fn echo_list_node_array(
        &mut self,
        value: Vec<Option<Box<ListNode>>>,
    ) -> Vec<Option<Box<ListNode>>> {
        value
    }

    pub fn echo_tree_node_list(
        &mut self,
        value: Vec<Option<Rc<RefCell<TreeNode>>>>,
    ) -> Vec<Option<Rc<RefCell<TreeNode>>>> {
        value
    }

    pub fn noop(&mut self, value: i32) {}
}
