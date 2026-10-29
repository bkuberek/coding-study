import shutil
import subprocess
from dataclasses import replace

import pytest

from coding_study.adapters.languages.rust.stub_generator import RustStubGenerator
from coding_study.adapters.languages.rust.types import rust_type
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.signature import FunctionSignature, Param, Returns
from coding_study.domain.type_dsl import parse_return_type, parse_value_type
from tests.stub_contract import GOLDENS, STUB_CASES, StubCase, check_stub, stub_cases


def stub_meta(case_name: str) -> ProblemMeta:
    return next(case for case in STUB_CASES if case.name == case_name).meta


def generate(case_name: str) -> str:
    return RustStubGenerator().generate(stub_meta(case_name))


@stub_cases
def test_rust_stub(stub_case: StubCase):
    check_stub(Language.RUST, stub_case, RustStubGenerator().generate(stub_case.meta))


@pytest.mark.parametrize(
    ("dsl", "expected"),
    [
        ("int", "i32"),
        ("long", "i64"),
        ("double", "f64"),
        ("bool", "bool"),
        ("string", "String"),
        ("char", "char"),
        ("char[][]", "Vec<Vec<char>>"),
        ("list<list<string>>", "Vec<Vec<String>>"),
        ("ListNode", "Option<Box<ListNode>>"),
        ("ListNode[]", "Vec<Option<Box<ListNode>>>"),
        ("TreeNode", "Option<Rc<RefCell<TreeNode>>>"),
        ("list<TreeNode>", "Vec<Option<Rc<RefCell<TreeNode>>>>"),
        ("GraphNode", "Option<Rc<RefCell<GraphNode>>>"),
        ("decimal", "Decimal"),
        ("list<date>", "Vec<NaiveDate>"),
        ("void", ""),
    ],
)
def test_rust_types_follow_the_mapping_table(dsl, expected):
    assert rust_type(parse_return_type(dsl)) == expected


def test_decimal_and_date_import_their_crates_types():
    stub = generate("conformance-decimal-date-types")
    assert "use chrono::NaiveDate;\nuse rust_decimal::Decimal;\n\npub struct TypeEcho" in stub
    assert "pub fn echo_decimal(&mut self, value: Decimal) -> Decimal {" in stub


def test_crate_imports_share_one_group_in_rustfmt_order():
    meta = stub_meta("invert-tree")
    assert isinstance(meta.signature, FunctionSignature)
    param = Param("since", parse_value_type("date"))
    dated = replace(meta, signature=replace(meta.signature, params=(*meta.signature.params, param)))
    stub = RustStubGenerator().generate(dated)
    assert "use std::rc::Rc;\n\nuse chrono::NaiveDate;\nuse cs_support::TreeNode;\n" in stub


def test_imports_only_the_node_types_used_after_rc_and_refcell():
    stub = generate("invert-tree")
    assert "use std::cell::RefCell;\nuse std::rc::Rc;\n\nuse cs_support::TreeNode;\n" in stub
    assert "use" not in generate("two-sum")
    assert "use cs_support::ListNode;\n" in generate("merge-k-lists")
    assert "Rc" not in generate("merge-k-lists")


def test_names_are_snake_case_with_new_as_the_constructor():
    assert "pub fn get_http_code(max_value: i32, user_id: String, utf8_text: String)" in (
        generate("naming")
    )
    assert "    pub fn new(capacity: i32) -> Self {\n        LRUCache {}\n" in generate("lru-cache")


def test_output_from_takes_the_parameter_by_mutable_reference():
    assert "pub fn rotate(nums: &mut Vec<i32>, k: i32) {" in generate("rotate")


def test_concurrent_methods_take_a_shared_reference():
    stub = generate("bounded-blocking-queue")
    assert "// Concurrency: threads\n" in stub
    assert "    pub fn take(&self) -> i32 {" in stub


def test_a_signature_longer_than_100_characters_is_split_like_rustfmt():
    long_type = parse_value_type("list<list<list<int>>>")
    signature = FunctionSignature(
        "echoNested",
        (Param("firstValue", long_type), Param("secondValue", long_type)),
        Returns(long_type),
    )
    stub = RustStubGenerator().generate(replace(stub_meta("two-sum"), signature=signature))
    assert (
        "pub fn echo_nested(\n"
        "    first_value: Vec<Vec<Vec<i32>>>,\n"
        "    second_value: Vec<Vec<Vec<i32>>>,\n"
        ") -> Vec<Vec<Vec<i32>>> {\n"
    ) in stub


@pytest.mark.skipif(shutil.which("rustfmt") is None, reason="rustfmt is not installed")
def test_goldens_are_rustfmt_clean():
    goldens = [GOLDENS.path(Language.RUST, case.name) for case in STUB_CASES]
    present = [str(path) for path in goldens if path.exists()]
    result = subprocess.run(
        ["rustfmt", "--check", "--edition", "2021", *present], capture_output=True, text=True
    )
    assert (result.returncode, result.stdout) == (0, "")
