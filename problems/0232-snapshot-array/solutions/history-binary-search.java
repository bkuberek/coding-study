import java.util.*;

public class SnapshotArray {
    // history.get(i) holds {snapshot id, value} pairs with strictly increasing snapshot ids.
    private final List<List<int[]>> history;
    private int snaps = 0;

    public SnapshotArray(int length) {
        history = new ArrayList<>(length);
        for (int i = 0; i < length; i++) {
            history.add(new ArrayList<>());
        }
    }

    public void set(int index, int value) {
        List<int[]> entries = history.get(index);
        if (!entries.isEmpty() && entries.get(entries.size() - 1)[0] == snaps) {
            entries.get(entries.size() - 1)[1] = value; // overwrite within the same snapshot
        } else {
            entries.add(new int[] {snaps, value});
        }
    }

    public int snap() {
        return snaps++;
    }

    public int get(int index, int snapId) {
        List<int[]> entries = history.get(index);
        // Upper bound: how many changes happened at or before snapId.
        int low = 0;
        int high = entries.size();
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (entries.get(middle)[0] <= snapId) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return low > 0 ? entries.get(low - 1)[1] : 0;
    }
}
