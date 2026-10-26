package cs.runner;

import com.google.gson.JsonElement;
import java.util.List;

/** Fresh call arguments for a member, including {@code ref_of} parameters. */
final class Arguments {
    private Arguments() {
    }

    /** {@code values} holds one JSON value per parameter, in declaration order. */
    static Object[] decode(Member member, List<JsonElement> values) {
        List<Member.Param> params = member.params();
        if (values.size() != params.size()) {
            throw new BadRequestException(
                    member.name() + " takes " + params.size() + " arguments, got " + values.size());
        }
        Object[] arguments = new Object[params.size()];
        for (int index = 0; index < params.size(); index++) {
            Member.Param param = params.get(index);
            if (param.refOf() == null) {
                arguments[index] = Values.decode(param.type(), values.get(index));
            }
        }
        for (int index = 0; index < params.size(); index++) {
            String refOf = params.get(index).refOf();
            if (refOf != null) {
                Object container = arguments[params.indexOf(member.param(refOf))];
                arguments[index] = referencedNode(container, values.get(index), refOf);
            }
        }
        return arguments;
    }

    /** The first node in {@code container}, in traversal order, whose val is {@code value}. */
    private static Object referencedNode(Object container, JsonElement value, String refOf) {
        if (value.isJsonNull()) {
            return null;
        }
        int val = Values.decodeInt(value);
        try {
            for (Object node : Nodes.traverse(container)) {
                if (Nodes.val(node) == val) {
                    return node;
                }
            }
        } catch (InvalidOutputException error) {
            throw new IllegalStateException(error);
        }
        throw new BadRequestException("no node with val " + val + " in " + refOf);
    }
}
