package cs.suite;

import cs.runner.SuiteSelection;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import org.junit.platform.engine.UniqueId;

/**
 * A test's id in the runner protocol (docs/specs/runners.md#suite-job), read from its JUnit
 * Platform unique id. Like every suite's, it names the test's file first, relative to the project
 * root: {@code src/test/java/bank/Level1Test.java::ex1}. A nested class, or a top-level class not
 * named like its file, comes before the method, joined by {@code " > "}
 * ({@code ...BankTest.java::Deposits > refusesNegative}), and each parameterized or dynamic
 * invocation adds {@code [n]} ({@code ...RateTest.java::rounds[2]}). A class reported on its own is
 * its file, or its file and class names.
 *
 * @param text the id as the runner reports it
 * @param classes the ids of the classes around it, outermost first; empty for an engine
 * @param method the test method's id, without invocations; null for a class or an engine
 */
record TestId(String text, List<String> classes, String method) {
    private static final Set<String> CLASS_SEGMENTS = Set.of("class", "nested-class");
    private static final Set<String> METHOD_SEGMENTS =
            Set.of("method", "test-factory", "test-template");
    private static final Set<String> INVOCATION_SEGMENTS =
            Set.of("test-template-invocation", "dynamic-test", "dynamic-container");
    private static final String NESTING = " > ";
    private static final char INVOCATION_MARKER = '#';

    static TestId of(UniqueId uniqueId, SourceFiles files) {
        String topClass = null;
        List<String> names = new ArrayList<>();
        List<Integer> classDepths = new ArrayList<>();
        String methodName = null;
        StringBuilder invocations = new StringBuilder();
        for (UniqueId.Segment segment : uniqueId.getSegments()) {
            String type = segment.getType();
            if (CLASS_SEGMENTS.contains(type) && topClass == null) {
                topClass = segment.getValue();
                classDepths.add(0);
            } else if (CLASS_SEGMENTS.contains(type)) {
                names.add(segment.getValue());
                classDepths.add(names.size());
            } else if (METHOD_SEGMENTS.contains(type)) {
                methodName = methodName(segment.getValue());
            } else if (INVOCATION_SEGMENTS.contains(type)) {
                invocations.append('[').append(invocation(segment.getValue())).append(']');
            }
        }
        if (topClass == null) {
            return new TestId(uniqueId.toString(), List.of(), null);
        }
        String file = files.of(topClass);
        String simpleName = topClass.substring(topClass.lastIndexOf('.') + 1);
        if (!simpleName.equals(stem(file))) {
            names.add(0, simpleName);
            classDepths.replaceAll(depth -> depth + 1);
        }
        List<String> classes = new ArrayList<>();
        for (int depth : classDepths) {
            classes.add(join(file, names.subList(0, depth)));
        }
        if (methodName == null) {
            return new TestId(classes.get(classes.size() - 1), List.copyOf(classes), null);
        }
        List<String> path = new ArrayList<>(names);
        path.add(methodName);
        String method = join(file, path);
        return new TestId(method + invocations, List.copyOf(classes), method);
    }

    /** Whether a restart leaves it out: it, or a class around it, was reported before. */
    boolean skippedBy(Set<String> skip) {
        return skip.contains(text) || classes.stream().anyMatch(skip::contains);
    }

    /**
     * Whether a restart leaves out every invocation of this parameterized or dynamic test:
     * running it again would report its earlier invocations a second time.
     */
    boolean hasInvocationIn(Set<String> skip) {
        return method != null && skip.stream().anyMatch(id -> id.startsWith(method + '['));
    }

    /** A parameterized or dynamic test's method, selected by its id or by one invocation's. */
    boolean methodSelectedBy(SuiteSelection selection) {
        if (method == null || selection.selects(method)) {
            return true;
        }
        String last = method.substring(method.lastIndexOf(SuiteSelection.ID_SEPARATOR) + 2);
        return selection.select().stream()
                .anyMatch(wanted -> wanted.startsWith(method + '[') || wanted.startsWith(last + '['));
    }

    private static String join(String file, List<String> names) {
        return names.isEmpty() ? file : file + SuiteSelection.ID_SEPARATOR + String.join(NESTING, names);
    }

    private static String stem(String file) {
        String name = file.substring(file.lastIndexOf('/') + 1);
        int extension = name.lastIndexOf('.');
        return extension < 0 ? name : name.substring(0, extension);
    }

    /** {@code ex1()} or {@code add(int, int)} as the method's name. */
    private static String methodName(String value) {
        int parameters = value.indexOf('(');
        return parameters < 0 ? value : value.substring(0, parameters);
    }

    /** {@code #2} as {@code 2}. */
    private static String invocation(String value) {
        return value.charAt(0) == INVOCATION_MARKER ? value.substring(1) : value;
    }
}
