from coding_study.domain.signature import (
    ClassSignature,
    FunctionSignature,
    Method,
    NodeSerialization,
    Param,
    Returns,
    SignatureIssue,
    modifier_issues,
)
from coding_study.domain.type_dsl import (
    ArrayType,
    NodeKind,
    NodeType,
    Scalar,
    ScalarType,
    VoidType,
)

INT = ScalarType(Scalar.INT)
LIST_NODE = NodeType(NodeKind.LIST_NODE)
TREE_NODE = NodeType(NodeKind.TREE_NODE)
HEAD = Param("head", LIST_NODE)


def function(*params: Param, returns: Returns) -> FunctionSignature:
    return FunctionSignature("solve", params, returns)


def test_plain_signature_has_no_issues():
    assert modifier_issues(function(Param("nums", INT), returns=Returns(INT))) == ()


def test_valid_modifiers_have_no_issues():
    signature = function(
        HEAD,
        Param("node", LIST_NODE, ref_of="head"),
        returns=Returns(LIST_NODE, serialize_as=NodeSerialization.INDEX, index_of="head"),
    )
    assert modifier_issues(signature) == ()


def test_ref_of_must_name_a_param():
    signature = function(Param("node", LIST_NODE, ref_of="root"), returns=Returns(INT))
    assert modifier_issues(signature) == (
        SignatureIssue("signature.function.params[0].ref_of", 'no parameter named "root"'),
    )


def test_ref_of_cannot_name_itself():
    signature = function(Param("node", LIST_NODE, ref_of="node"), returns=Returns(INT))
    assert modifier_issues(signature) == (
        SignatureIssue("signature.function.params[0].ref_of", "must name another parameter"),
    )


def test_ref_of_needs_a_node_typed_param():
    signature = function(HEAD, Param("value", INT, ref_of="head"), returns=Returns(INT))
    assert modifier_issues(signature) == (
        SignatureIssue(
            "signature.function.params[1].ref_of",
            'only allowed on a node-typed parameter, not "int"',
        ),
    )


def test_ref_of_must_name_the_same_node_type():
    signature = function(
        Param("root", TREE_NODE), Param("node", LIST_NODE, ref_of="root"), returns=Returns(INT)
    )
    assert modifier_issues(signature) == (
        SignatureIssue(
            "signature.function.params[1].ref_of", '"root" is "TreeNode", not "ListNode"'
        ),
    )


def test_output_from_must_name_a_param():
    signature = function(
        Param("nums", ArrayType(INT)), returns=Returns(VoidType(), output_from="values")
    )
    assert modifier_issues(signature) == (
        SignatureIssue("signature.function.returns.output_from", 'no parameter named "values"'),
    )


def test_output_from_needs_a_void_return():
    signature = function(Param("nums", ArrayType(INT)), returns=Returns(INT, output_from="nums"))
    assert modifier_issues(signature) == (
        SignatureIssue(
            "signature.function.returns.output_from", 'only allowed with type void, not "int"'
        ),
    )


def test_as_needs_a_node_typed_return():
    signature = function(HEAD, returns=Returns(INT, serialize_as=NodeSerialization.VALUE))
    assert modifier_issues(signature) == (
        SignatureIssue(
            "signature.function.returns.as", 'only allowed on a node-typed return, not "int"'
        ),
    )


def test_of_must_name_a_param():
    signature = function(
        HEAD,
        returns=Returns(LIST_NODE, serialize_as=NodeSerialization.INDEX, index_of="list"),
    )
    assert modifier_issues(signature) == (
        SignatureIssue("signature.function.returns.of", 'no parameter named "list"'),
    )


def test_of_requires_as_index():
    signature = function(
        HEAD,
        returns=Returns(LIST_NODE, serialize_as=NodeSerialization.VALUE, index_of="head"),
    )
    assert modifier_issues(signature) == (
        SignatureIssue("signature.function.returns.of", "only allowed with as: index"),
    )


def test_no_alias_with_must_name_a_param():
    signature = function(HEAD, returns=Returns(LIST_NODE, no_alias_with="original"))
    assert modifier_issues(signature) == (
        SignatureIssue("signature.function.returns.no_alias_with", 'no parameter named "original"'),
    )


def test_class_issues_name_constructor_and_method_locations():
    signature = ClassSignature(
        "Walker",
        (Param("node", LIST_NODE, ref_of="head"),),
        (Method("step", (HEAD,), Returns(INT, output_from="cursor")),),
    )
    assert [issue.location for issue in modifier_issues(signature)] == [
        "signature.class.constructor.params[0].ref_of",
        "signature.class.methods[0].returns.output_from",
    ]


def test_method_modifiers_resolve_against_the_method_params():
    signature = ClassSignature(
        "Walker",
        (HEAD,),
        (Method("step", (), Returns(VoidType(), output_from="head")),),
    )
    assert modifier_issues(signature) == (
        SignatureIssue(
            "signature.class.methods[0].returns.output_from", 'no parameter named "head"'
        ),
    )
