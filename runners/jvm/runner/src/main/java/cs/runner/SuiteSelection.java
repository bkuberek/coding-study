package cs.runner;

import java.util.List;
import java.util.Set;

/**
 * The tests a suite job runs (docs/specs/runners.md#suite-job).
 *
 * @param select test ids, or their last part after {@code ::}; empty: every test
 * @param skip test ids, and the ids of classes whose tests are all left out, set on a restart
 */
public record SuiteSelection(List<String> select, Set<String> skip) {
    /** The separator between a test's class and its method in a test id. */
    public static final String ID_SEPARATOR = "::";

    public SuiteSelection {
        select = List.copyOf(select);
        skip = Set.copyOf(skip);
    }

    /** Whether {@code select} names the test, by its whole id or its last part. */
    public boolean selects(String testId) {
        return select.isEmpty()
                || select.stream().anyMatch(
                        wanted -> testId.equals(wanted) || testId.endsWith(ID_SEPARATOR + wanted));
    }
}
