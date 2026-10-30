from dataclasses import replace
from pathlib import Path

import yaml

from coding_study.adapters.languages.rust.bridge import (
    LIST_IDENTITY,
    SHARED_NODES_REASON,
    BridgeTarget,
    Unavailable,
    bridge_source,
    rust_string,
    unsupported_reason,
)
from coding_study.adapters.problem_documents import meta_from_document
from coding_study.domain.problem import ProblemKind, ProblemMeta
from coding_study.domain.signature import Signature
from tests.helpers import REPOSITORY_ROOT
from tests.stub_contract import STUB_CASES

USER = BridgeTarget("user", "user", Path("/ws/rust/practice/two_sum.rs"))
REFERENCE = BridgeTarget("ref/hash-map", "ref_hash_map", Path("/ws/.cs/build/rust/ref/hash_map.rs"))
CONFORMANCE = REPOSITORY_ROOT / "runners" / "conformance"


def stub_meta(case_name: str) -> ProblemMeta:
    return next(case.meta for case in STUB_CASES if case.name == case_name)


def stub_signature(case_name: str) -> Signature:
    return stub_meta(case_name).signature


def fixture_signature(directory: str) -> Signature:
    document = yaml.safe_load((CONFORMANCE / directory / "meta.yaml").read_text())
    return meta_from_document(document, "meta.yaml").signature


def text(
    signature: Signature, *targets: BridgeTarget, kind: ProblemKind = ProblemKind.DESIGN
) -> str:
    return bridge_source(signature, targets or (USER,), kind=kind).text


def test_brings_each_target_in_as_a_path_module():
    bridge = text(stub_signature("two-sum"), USER, REFERENCE)
    assert '#[path = "/ws/rust/practice/two_sum.rs"]\nmod user;\n' in bridge
    assert "mod ref_hash_map;\n" in bridge


def test_a_function_decodes_each_argument_by_name_with_its_declared_type():
    bridge = text(stub_signature("two-sum"))
    assert '    let arg_nums: Vec<i32> = args.named("nums")?;\n' in bridge
    assert "        let output: Vec<i32> = user::two_sum(arg_nums, arg_target);\n" in bridge
    assert "entry: cs_runner::Entry::Function(user_call)," in bridge


def test_a_class_constructs_with_new_and_matches_each_operation():
    bridge = text(stub_signature("lru-cache"))
    assert "let instance: user::LRUCache = user::LRUCache::new(arg_capacity);" in bridge
    assert '        "put" => {\n            args.count(2, "put")?;\n' in bridge
    assert "let output: () = instance.put(arg_key, arg_value);" in bridge
    assert "_ => Err(cs_runner::InputError::unknown_op(op))," in bridge


def test_a_concurrent_class_is_shared_with_the_worker_threads():
    meta = stub_meta("bounded-blocking-queue")
    bridge = text(meta.signature, kind=meta.kind)
    assert "Result<cs_runner::SharedConstruct, cs_runner::InputError> {" in bridge
    assert "        cs_runner::shared(instance)\n" in bridge
    assert "Ok(Box::new(move |object: &(dyn std::any::Any + Send + Sync)| {" in bridge
    assert "cs_runner::shared_instance::<user::BoundedBlockingQueue>(object);" in bridge
    assert "let output: i32 = instance.take();" in bridge
    assert (
        'cs_runner::Entry::Concurrent(cs_runner::Concurrent { name: "BoundedBlockingQueue",'
        in bridge
    )


def test_method_names_are_snake_case_and_operations_canonical():
    bridge = text(stub_signature("progressive"))
    assert '"scanByPrefix" => {' in bridge
    assert "instance.scan_by_prefix(arg_timestamp, arg_key, arg_prefix)" in bridge


def test_keyword_names_are_called_as_raw_identifiers_and_operations_stay_canonical():
    bridge = text(stub_signature("keyword-names"))
    assert "let instance: user::Robot = user::Robot::new(arg_ref);" in bridge
    assert '        "move" => {\n            args.count(1, "move")?;\n' in bridge
    assert "let output: i32 = instance.r#move(arg_steps);" in bridge
    assert "let output: () = instance.r#loop(arg_match);" in bridge


def test_a_function_named_after_a_keyword_is_called_as_a_raw_identifier():
    signature = replace(stub_signature("two-sum"), name="match")
    assert "user::r#match(arg_nums, arg_target);" in text(signature)


def test_output_from_passes_a_mutable_reference_and_encodes_the_argument():
    bridge = text(stub_signature("rotate"))
    assert '    let mut arg_nums: Vec<i32> = args.named("nums")?;\n' in bridge
    assert "user::rotate(&mut arg_nums, arg_k);" in bridge
    assert "cs_runner::output(arg_nums)" in bridge


def test_ref_of_looks_the_node_up_after_the_argument_it_points_into():
    bridge = text(fixture_signature("9011-conformance-ref-of-tree"))
    root = bridge.index('let arg_root: Option<Rc<RefCell<TreeNode>>> = args.named("root")?;')
    node = bridge.index('args.node_in(1, "node", &arg_root, "root")?;')
    assert root < node
    assert "cs_runner::output(cs_runner::ValueOf(output))" in bridge


def test_no_alias_with_takes_the_addresses_first_and_retains_freed_memory():
    bridge = text(fixture_signature("9013-conformance-no-alias"))
    assert "let nodes_of_head = cs_runner::Identity::of(&arg_head);" in bridge
    assert "cs_runner::retaining(|| user::copy_list(arg_head))" in bridge
    assert 'cs_runner::NoAlias::new(output, nodes_of_head, "head")' in bridge


def test_identity_on_list_nodes_is_unsupported():
    signature = fixture_signature("9010-conformance-ref-of-list")
    assert unsupported_reason(signature, ProblemKind.DESIGN) == LIST_IDENTITY
    assert 'error_type: "UnsupportedType"' in text(signature)


def test_decimal_and_date_are_spelled_with_their_crates_types():
    signature = stub_signature("conformance-decimal-date-types")
    assert unsupported_reason(signature, ProblemKind.DESIGN) is None
    bridge = text(signature)
    assert "use chrono::NaiveDate;\nuse rust_decimal::Decimal;\n" in bridge
    assert 'let arg_value: Vec<NaiveDate> = args.at(0, "value")?;' in bridge


def test_node_types_are_unsupported_in_concurrent_problems():
    signature = stub_signature("conformance-types")
    assert unsupported_reason(signature, ProblemKind.DESIGN) is None
    assert unsupported_reason(signature, ProblemKind.CONCURRENT) == SHARED_NODES_REASON


def test_an_unavailable_target_keeps_its_module_but_has_no_call():
    failed = replace(USER, unavailable=Unavailable("SymbolNotFound", 'no `two_sum` in "x"'))
    bridge = text(stub_signature("two-sum"), failed)
    assert ("mod user;" in bridge, "fn user_call" in bridge) == (True, False)
    assert 'message: "no `two_sum` in \\"x\\"" }' in bridge


def test_a_target_without_its_module_leaves_it_out():
    bridge = text(stub_signature("two-sum"), replace(USER, with_module=False))
    assert "mod user;" not in bridge


def test_owners_map_each_target_line_to_its_target():
    bridge = bridge_source(stub_signature("two-sum"), (USER, REFERENCE), kind=ProblemKind.FUNCTION)
    lines = bridge.text.splitlines()
    call = next(n for n, line in enumerate(lines, 1) if "ref_hash_map::two_sum(" in line)
    module = next(n for n, line in enumerate(lines, 1) if line == "mod user;")
    assert (bridge.owners[call], bridge.modules[module]) == ("ref/hash-map", "user")


def test_string_literals_escape_like_rust():
    assert rust_string('a"b\\c\n\x01') == '"a\\"b\\\\c\\n\\u{1}"'
