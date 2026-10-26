package cs.runner;

import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonPrimitive;
import java.lang.reflect.Array;
import java.util.List;
import java.util.Set;

/** Serializes what a call produced, honoring the return modifiers (problem-format.md#modifiers). */
final class Outputs {
    private static final int NOT_FOUND = -1;

    private Outputs() {
    }

    /**
     * Input structure captured before the call, so the user cannot change the answer by rewiring
     * the input: the nodes of the {@code no_alias_with} parameter and the traversal order of the
     * {@code of} parameter (lists along {@code next}, trees in level order, graphs breadth-first).
     */
    record Snapshot(Set<Object> aliasCandidates, List<Object> indexOrder) {
    }

    static Snapshot beforeCall(Member member, Object[] arguments) {
        Member.Returns returns = member.returns();
        Set<Object> aliasCandidates = Nodes.identitySet();
        List<Object> indexOrder = List.of();
        try {
            if (returns.noAliasWith() != null) {
                Member.Param param = member.param(returns.noAliasWith());
                collectNodes(param.type(), argument(member, arguments, param), aliasCandidates);
            }
            if (Member.Returns.AS_INDEX.equals(returns.serializeAs())) {
                Member.Param param = member.param(returns.indexOf());
                indexOrder = Nodes.traverse(argument(member, arguments, param));
            }
        } catch (InvalidOutputException error) {
            throw new IllegalStateException("decoded inputs are always well formed", error);
        }
        return new Snapshot(aliasCandidates, indexOrder);
    }

    static JsonElement serialize(
            Member member, Object[] arguments, Object returned, Snapshot snapshot)
            throws InvalidOutputException {
        Member.Returns returns = member.returns();
        if (returns.isVoid()) {
            return returns.outputFrom() == null
                    ? JsonNull.INSTANCE
                    : Values.encode(member.param(returns.outputFrom()).type(),
                            argument(member, arguments, member.param(returns.outputFrom())));
        }
        if (returns.noAliasWith() != null) {
            requireNoAlias(returns, returned, snapshot.aliasCandidates());
        }
        if (Member.Returns.AS_VALUE.equals(returns.serializeAs())) {
            Object node = requireInstance(returns.type(), returned);
            return node == null ? JsonNull.INSTANCE : new JsonPrimitive(Nodes.val(node));
        }
        if (Member.Returns.AS_INDEX.equals(returns.serializeAs())) {
            Object node = requireInstance(returns.type(), returned);
            return new JsonPrimitive(indexOf(node, snapshot.indexOrder(), returns.indexOf()));
        }
        return Values.encode(returns.type(), returned);
    }

    private static Object argument(Member member, Object[] arguments, Member.Param param) {
        return arguments[member.params().indexOf(param)];
    }

    private static void requireNoAlias(Member.Returns returns, Object returned, Set<Object> inputs)
            throws InvalidOutputException {
        Set<Object> outputs = Nodes.identitySet();
        collectNodes(returns.type(), returned, outputs);
        for (Object node : outputs) {
            if (inputs.contains(node)) {
                throw new InvalidOutputException(
                        "the returned structure shares nodes with " + returns.noAliasWith());
            }
        }
    }

    /** The returned node's position in the {@code of} parameter's traversal order. */
    private static int indexOf(Object returned, List<Object> order, String of)
            throws InvalidOutputException {
        if (returned == null) {
            return NOT_FOUND;
        }
        for (int index = 0; index < order.size(); index++) {
            if (order.get(index) == returned) {
                return index;
            }
        }
        throw new InvalidOutputException("the returned node is not a node of \"" + of + "\"");
    }

    private static void collectNodes(DslType type, Object value, Set<Object> into)
            throws InvalidOutputException {
        switch (type) {
            case DslType.Node node -> into.addAll(Nodes.traverse(requireInstance(node, value)));
            case DslType.ArrayOf array when value != null && value.getClass().isArray() -> {
                for (int index = 0; index < Array.getLength(value); index++) {
                    collectNodes(array.element(), Array.get(value, index), into);
                }
            }
            case DslType.ListOf list when value instanceof List<?> items -> {
                for (Object item : items) {
                    collectNodes(list.element(), item, into);
                }
            }
            default -> {
            }
        }
    }

    private static Object requireInstance(DslType type, Object value)
            throws InvalidOutputException {
        if (value != null && !type.jvmClass().isInstance(value)) {
            throw new InvalidOutputException(
                    "expected " + type + ", got " + value.getClass().getName());
        }
        return value;
    }
}
