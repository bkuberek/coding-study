from coding_study.domain.signature import (
    ClassSignature,
    FunctionSignature,
    Method,
    NodeSerialization,
    Param,
    Returns,
    declared_types,
    output_type,
)
from coding_study.domain.type_dsl import (
    ArrayType,
    NodeKind,
    NodeType,
    Scalar,
    ScalarType,
    VoidType,
)

DECIMAL = ScalarType(Scalar.DECIMAL)
DATES = ArrayType(ScalarType(Scalar.DATE))
LIST_NODE = NodeType(NodeKind.LIST_NODE)


def test_declared_types_of_a_function_are_its_params_then_its_return():
    signature = FunctionSignature("total", (Param("days", DATES),), Returns(DECIMAL))
    assert list(declared_types(signature)) == [DATES, DECIMAL]


def test_declared_types_of_a_class_cover_the_constructor_and_every_method():
    get = Method("get", (Param("day", DATES),), Returns(DECIMAL))
    signature = ClassSignature("Table", (Param("head", LIST_NODE),), (get,))
    assert list(declared_types(signature)) == [LIST_NODE, DATES, DECIMAL]


def test_output_type_is_the_return_type():
    amounts = Param("amounts", ArrayType(DECIMAL))
    signature = FunctionSignature("total", (amounts,), Returns(DECIMAL))
    assert output_type(signature) == DECIMAL


def test_output_type_of_an_output_from_member_is_its_parameter_type():
    method = Method("sortDays", (Param("days", DATES),), Returns(VoidType(), output_from="days"))
    assert output_type(method) == DATES


def test_a_void_member_has_no_output_type():
    assert output_type(Method("reset", (), Returns(VoidType()))) is None


def test_a_node_returned_as_a_value_has_no_output_type():
    returns = Returns(LIST_NODE, serialize_as=NodeSerialization.VALUE)
    assert output_type(FunctionSignature("middle", (Param("head", LIST_NODE),), returns)) is None
