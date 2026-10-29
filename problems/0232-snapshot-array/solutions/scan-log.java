import java.util.*;

public class SnapshotArray {
    // Each entry is {index, value, snapshots taken before the write}.
    private final List<int[]> log = new ArrayList<>();
    private int snaps = 0;

    public SnapshotArray(int length) {
    }

    public void set(int index, int value) {
        log.add(new int[] {index, value, snaps});
    }

    public int snap() {
        return snaps++;
    }

    public int get(int index, int snapId) {
        // The newest write to index that happened before snapshot snapId was taken.
        for (int i = log.size() - 1; i >= 0; i--) {
            int[] write = log.get(i);
            if (write[0] == index && write[2] <= snapId) {
                return write[1];
            }
        }
        return 0;
    }
}
