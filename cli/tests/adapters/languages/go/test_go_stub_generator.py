import shutil
import subprocess
from dataclasses import replace

import pytest

from coding_study.adapters.languages.go import create_stub_generator
from coding_study.adapters.languages.go.stub_generator import go_type
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.signature import ClassSignature, FunctionSignature, Method, Param, Returns
from coding_study.domain.type_dsl import parse_return_type, parse_value_type
from tests.stub_contract import GOLDENS, STUB_CASES, StubCase, check_stub, stub_cases


def stub_meta(case_name: str) -> ProblemMeta:
    return next(case for case in STUB_CASES if case.name == case_name).meta


def generate(case_name: str) -> str:
    return create_stub_generator().generate(stub_meta(case_name))


@stub_cases
def test_go_stub(stub_case: StubCase):
    check_stub(Language.GO, stub_case, create_stub_generator().generate(stub_case.meta))


@pytest.mark.parametrize(
    ("dsl", "expected"),
    [
        ("int", "int"),
        ("long", "int64"),
        ("double", "float64"),
        ("char", "rune"),
        ("char[][]", "[][]rune"),
        ("list<list<string>>", "[][]string"),
        ("ListNode", "*ListNode"),
        ("list<TreeNode>", "[]*TreeNode"),
        ("decimal", "decimal.Decimal"),
        ("list<date>", "[]time.Time"),
        ("void", ""),
    ],
)
def test_go_types_follow_the_mapping_table(dsl, expected):
    assert go_type(parse_return_type(dsl)) == expected


def test_decimal_and_date_import_their_packages_as_goimports_groups_them():
    stub = generate("conformance-decimal-date-types")
    assert 'import (\n\t"time"\n\n\t"github.com/shopspring/decimal"\n)\n' in stub
    assert "func (e *TypeEcho) EchoDecimal(value decimal.Decimal) decimal.Decimal {" in stub


def test_a_single_package_is_imported_on_one_line():
    meta = stub_meta("two-sum")
    assert isinstance(meta.signature, FunctionSignature)
    param = Param("day", parse_value_type("date"))
    dated = replace(meta, signature=replace(meta.signature, params=(param,)))
    assert '\nimport "time"\n\nfunc twoSum(day time.Time) []int {' in (
        create_stub_generator().generate(dated)
    )


def test_the_support_package_groups_with_the_standard_library():
    meta = stub_meta("invert-tree")
    assert isinstance(meta.signature, FunctionSignature)
    param = Param("since", parse_value_type("date"))
    dated = replace(meta, signature=replace(meta.signature, params=(*meta.signature.params, param)))
    stub = create_stub_generator().generate(dated)
    assert 'import (\n\t"cstudy/support"\n\t"time"\n)\n\ntype TreeNode' in stub


def test_imports_support_only_for_the_node_types_used():
    stub = generate("invert-tree")
    assert 'import "cstudy/support"\n\ntype TreeNode = support.TreeNode\n' in stub
    assert "ListNode" not in stub
    assert "import" not in generate("two-sum")


def test_functions_stay_unexported_and_methods_are_exported():
    assert "func twoSum(nums []int, target int) []int {" in generate("two-sum")
    assert "func (c *LRUCache) Get(key int) int {" in generate("lru-cache")


def test_the_receiver_avoids_a_parameter_name():
    meta = stub_meta("lru-cache")
    assert isinstance(meta.signature, ClassSignature)
    param = Param("c", parse_value_type("int"))
    method = Method("get", (param,), Returns(parse_return_type("int")))
    clash = replace(meta, signature=replace(meta.signature, methods=(method,)))
    assert "func (l *LRUCache) Get(c int) int {" in create_stub_generator().generate(clash)


@pytest.mark.skipif(shutil.which("gofmt") is None, reason="gofmt is not installed")
def test_goldens_are_gofmt_clean():
    goldens = [GOLDENS.path(Language.GO, case.name) for case in STUB_CASES]
    present = [str(path) for path in goldens if path.exists()]
    result = subprocess.run(["gofmt", "-l", *present], capture_output=True, text=True, check=True)
    assert result.stdout == ""
