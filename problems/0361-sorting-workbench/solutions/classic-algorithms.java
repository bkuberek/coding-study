import java.util.*;

/**
 * Four classic sorts, each written the way the statement specifies it, with a meter that counts
 * the work of the latest sort. A sort returns a new array and never changes its input.
 */
public class SortingWorkbench {
    private int[] meter = new int[0];
    private int mergeComparisons;

    public SortingWorkbench() {
    }

    // Level 1
    public int[] insertionSort(int[] values) {
        int[] items = values.clone();
        int comparisons = 0;
        int moves = 0;
        for (int i = 1; i < items.length; i++) {
            int key = items[i];
            int j = i - 1;
            while (j >= 0) {
                comparisons++;
                if (items[j] <= key) {
                    break;
                }
                items[j + 1] = items[j];
                moves++;
                j--;
            }
            items[j + 1] = key;
        }
        meter = new int[] {comparisons, moves};
        return items;
    }

    public int[] report() {
        return meter.clone();
    }

    // Level 2
    public int[][] mergeSortBy(int[][] rows, int key) {
        mergeComparisons = 0;
        List<int[]> merged = mergeSort(new ArrayList<>(Arrays.asList(rows)), key);
        meter = new int[] {mergeComparisons};
        int[][] result = new int[merged.size()][];
        for (int i = 0; i < result.length; i++) {
            result[i] = merged.get(i).clone();
        }
        return result;
    }

    private List<int[]> mergeSort(List<int[]> rows, int key) {
        if (rows.size() <= 1) {
            return new ArrayList<>(rows);
        }
        int middle = rows.size() / 2;
        List<int[]> left = mergeSort(rows.subList(0, middle), key);
        List<int[]> right = mergeSort(rows.subList(middle, rows.size()), key);
        List<int[]> merged = new ArrayList<>(rows.size());
        int i = 0;
        int j = 0;
        while (i < left.size() && j < right.size()) {
            mergeComparisons++;
            if (left.get(i)[key] <= right.get(j)[key]) {
                merged.add(left.get(i++));
            } else {
                merged.add(right.get(j++));
            }
        }
        while (i < left.size()) {
            merged.add(left.get(i++));
        }
        while (j < right.size()) {
            merged.add(right.get(j++));
        }
        return merged;
    }

    // Level 3
    public int[] quickSort(int[] values) {
        int[] items = values.clone();
        int calls = 0;
        int steps = 0;
        Deque<int[]> ranges = new ArrayDeque<>();
        ranges.push(new int[] {0, items.length - 1});
        while (!ranges.isEmpty()) {
            int[] range = ranges.pop();
            int low = range[0];
            int high = range[1];
            if (high - low < 1) {
                continue;
            }
            int[] bounds = partition(items, low, high);
            calls++;
            steps += high - low + 1;
            ranges.push(new int[] {low, bounds[0] - 1});
            ranges.push(new int[] {bounds[1] + 1, high});
        }
        meter = new int[] {calls, steps};
        return items;
    }

    public int quickSelect(int[] values, int k) {
        int[] items = values.clone();
        int target = k - 1;
        int calls = 0;
        int steps = 0;
        int low = 0;
        int high = items.length - 1;
        while (low < high) {
            int[] bounds = partition(items, low, high);
            calls++;
            steps += high - low + 1;
            if (target < bounds[0]) {
                high = bounds[0] - 1;
            } else if (target > bounds[1]) {
                low = bounds[1] + 1;
            } else {
                break;
            }
        }
        meter = new int[] {calls, steps};
        return items[target];
    }

    /** Returns {below, above}: items[low..below-1] < pivot, items[below..above] == pivot, the rest > pivot. */
    private int[] partition(int[] items, int low, int high) {
        int pivot = items[low + (high - low) / 2];
        int below = low;
        int i = low;
        int above = high;
        while (i <= above) {
            if (items[i] < pivot) {
                int swap = items[below];
                items[below] = items[i];
                items[i] = swap;
                below++;
                i++;
            } else if (items[i] > pivot) {
                int swap = items[i];
                items[i] = items[above];
                items[above] = swap;
                above--;
            } else {
                i++;
            }
        }
        return new int[] {below, above};
    }

    // Level 4
    public int[] externalSort(int[] values, int memory, int ways) {
        List<int[]> runs = new ArrayList<>();
        for (int start = 0; start < values.length; start += memory) {
            int[] run = Arrays.copyOfRange(values, start, Math.min(start + memory, values.length));
            Arrays.sort(run);
            runs.add(run);
        }
        int initialRuns = runs.size();
        int passes = 0;
        while (runs.size() > 1) {
            List<int[]> next = new ArrayList<>();
            for (int start = 0; start < runs.size(); start += ways) {
                next.add(mergeGroup(runs.subList(start, Math.min(start + ways, runs.size()))));
            }
            runs = next;
            passes++;
        }
        meter = new int[] {initialRuns, passes};
        return runs.isEmpty() ? new int[0] : runs.get(0);
    }

    /** A min-heap of {value, run, position in the run} holds the front value of each run. */
    private int[] mergeGroup(List<int[]> group) {
        PriorityQueue<int[]> heap = new PriorityQueue<>(
                (a, b) -> a[0] != b[0] ? Integer.compare(a[0], b[0]) : Integer.compare(a[1], b[1]));
        int total = 0;
        for (int index = 0; index < group.size(); index++) {
            heap.add(new int[] {group.get(index)[0], index, 0});
            total += group.get(index).length;
        }
        int[] merged = new int[total];
        int written = 0;
        while (!heap.isEmpty()) {
            int[] front = heap.poll();
            merged[written++] = front[0];
            int[] run = group.get(front[1]);
            if (front[2] + 1 < run.length) {
                heap.add(new int[] {run[front[2] + 1], front[1], front[2] + 1});
            }
        }
        return merged;
    }
}
