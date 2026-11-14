package bank;

import java.util.ArrayList;
import java.util.List;
import java.util.OptionalLong;

/** An account's balance after each change, in time order. */
final class BalanceHistory {
    private record Change(long at, long balance) {}

    private final List<Change> changes = new ArrayList<>();

    /** Appends a change; {@code at} is never earlier than the last change's. */
    void record(long at, long balance) {
        changes.add(new Change(at, balance));
    }

    /**
     * The balance after the last change at or before {@code moment}; empty when {@code moment}
     * comes before the first change.
     */
    OptionalLong at(long moment) {
        int after = firstChangeAfter(moment);
        if (after == 0) {
            return OptionalLong.empty();
        }
        return OptionalLong.of(changes.get(after - 1).balance());
    }

    /** The index of the first change later than {@code moment}, or the size when there is none. */
    private int firstChangeAfter(long moment) {
        int low = 0;
        int high = changes.size();
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (changes.get(middle).at() <= moment) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return low;
    }
}
