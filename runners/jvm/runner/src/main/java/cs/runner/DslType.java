package cs.runner;

import cs.support.GraphNode;
import cs.support.ListNode;
import cs.support.TreeNode;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

/** A type from the signature DSL (docs/specs/problem-format.md#type-dsl). */
sealed interface DslType permits DslType.Scalar, DslType.ArrayOf, DslType.ListOf, DslType.Node {

    /** The JVM class of a parameter of this type: the Java column of the mapping table. */
    Class<?> jvmClass();

    static DslType parse(String text) {
        if (text.startsWith(ListOf.PREFIX) && text.endsWith(ListOf.SUFFIX)) {
            String element = text.substring(ListOf.PREFIX.length(), text.length() - 1);
            return new ListOf(parse(element));
        }
        if (text.endsWith(ArrayOf.SUFFIX)) {
            return new ArrayOf(parse(text.substring(0, text.length() - ArrayOf.SUFFIX.length())));
        }
        for (ScalarKind kind : ScalarKind.values()) {
            if (kind.dslName.equals(text)) {
                return new Scalar(kind);
            }
        }
        for (NodeKind kind : NodeKind.values()) {
            if (kind.dslName.equals(text)) {
                return new Node(kind);
            }
        }
        throw new BadRequestException("unknown type \"" + text + "\"");
    }

    enum ScalarKind {
        INT("int", int.class),
        LONG("long", long.class),
        DOUBLE("double", double.class),
        BOOL("bool", boolean.class),
        STRING("string", String.class),
        CHAR("char", char.class),
        DECIMAL("decimal", BigDecimal.class),
        DATE("date", LocalDate.class);

        final String dslName;
        final Class<?> jvmClass;

        ScalarKind(String dslName, Class<?> jvmClass) {
            this.dslName = dslName;
            this.jvmClass = jvmClass;
        }
    }

    enum NodeKind {
        LIST_NODE("ListNode", ListNode.class),
        TREE_NODE("TreeNode", TreeNode.class),
        GRAPH_NODE("GraphNode", GraphNode.class);

        final String dslName;
        final Class<?> jvmClass;

        NodeKind(String dslName, Class<?> jvmClass) {
            this.dslName = dslName;
            this.jvmClass = jvmClass;
        }
    }

    record Scalar(ScalarKind kind) implements DslType {
        @Override
        public Class<?> jvmClass() {
            return kind.jvmClass;
        }

        @Override
        public String toString() {
            return kind.dslName;
        }
    }

    record ArrayOf(DslType element) implements DslType {
        static final String SUFFIX = "[]";

        @Override
        public Class<?> jvmClass() {
            return element.jvmClass().arrayType();
        }

        @Override
        public String toString() {
            return element + SUFFIX;
        }
    }

    record ListOf(DslType element) implements DslType {
        static final String PREFIX = "list<";
        static final String SUFFIX = ">";

        @Override
        public Class<?> jvmClass() {
            return List.class;
        }

        @Override
        public String toString() {
            return PREFIX + element + SUFFIX;
        }
    }

    record Node(NodeKind kind) implements DslType {
        @Override
        public Class<?> jvmClass() {
            return kind.jvmClass;
        }

        @Override
        public String toString() {
            return kind.dslName;
        }
    }
}
