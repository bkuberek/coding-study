import java.util.Arrays;

// Arrays.binarySearch returns the index of *a* match, or encodes where an absent key would go
// as -(insertion point) - 1. Among duplicates, which match it returns is not specified.
public class ArraysSearch {
    public static void main(String[] args) {
        int[] weights = {3, 5, 5, 8, 8, 8, 12, 15, 19, 19, 24, 30};

        int found = Arrays.binarySearch(weights, 8);
        System.out.println("search 8: holds 8? " + (weights[found] == 8)
                + ", inside positions 3..5? " + (found >= 3 && found <= 5));

        for (int key : new int[] {10, 1, 99}) {
            int result = Arrays.binarySearch(weights, key);
            int insertionPoint = -result - 1;
            System.out.println("search " + key + ": " + result + ", so it would go at " + insertionPoint);
        }

        System.out.println("first 8, written by hand: " + lowerBound(weights, 8));
    }

    // The first index whose value is >= key, on the half-open interval [lo, hi).
    static int lowerBound(int[] a, int key) {
        int lo = 0;
        int hi = a.length;
        while (lo < hi) {
            int mid = (lo + hi) >>> 1;
            if (a[mid] >= key) {
                hi = mid;
            } else {
                lo = mid + 1;
            }
        }
        return lo;
    }
}
