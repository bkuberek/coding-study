import java.util.*;

public class RangeModule {
    // Disjoint, non-touching half-open intervals {start, end}, sorted by start.
    private List<int[]> intervals = new ArrayList<>();

    public RangeModule() {
    }

    public void addRange(int left, int right) {
        List<int[]> merged = new ArrayList<>(intervals.size() + 1);
        boolean placed = false;
        for (int[] interval : intervals) {
            if (interval[1] < left) {
                merged.add(interval);
            } else if (right < interval[0]) {
                if (!placed) {
                    merged.add(new int[] {left, right});
                    placed = true;
                }
                merged.add(interval);
            } else {
                // Overlapping or touching: absorb it into the new interval.
                left = Math.min(left, interval[0]);
                right = Math.max(right, interval[1]);
            }
        }
        if (!placed) {
            merged.add(new int[] {left, right});
        }
        intervals = merged;
    }

    public boolean queryRange(int left, int right) {
        // Stored intervals never touch, so a covered range lies inside a single one.
        for (int[] interval : intervals) {
            if (interval[0] <= left && right <= interval[1]) {
                return true;
            }
        }
        return false;
    }

    public void removeRange(int left, int right) {
        List<int[]> kept = new ArrayList<>(intervals.size() + 1);
        for (int[] interval : intervals) {
            if (interval[1] <= left || right <= interval[0]) {
                kept.add(interval);
                continue;
            }
            if (interval[0] < left) {
                kept.add(new int[] {interval[0], left});
            }
            if (right < interval[1]) {
                kept.add(new int[] {right, interval[1]});
            }
        }
        intervals = kept;
    }
}
