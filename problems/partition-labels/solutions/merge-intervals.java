import java.util.*;

public class Solution {
    public int[] partitionLabels(String s) {
        // Each letter occupies the span from its first to its last copy.
        int[] first = new int[26];
        int[] last = new int[26];
        Arrays.fill(first, -1);
        List<Integer> order = new ArrayList<>(); // letters by first occurrence: spans sorted by start
        for (int index = 0; index < s.length(); index++) {
            int letter = s.charAt(index) - 'a';
            if (first[letter] == -1) {
                first[letter] = index;
                order.add(letter);
            }
            last[letter] = index;
        }
        List<Integer> sizes = new ArrayList<>();
        int pieceStart = 0;
        int pieceEnd = -1;
        for (int letter : order) {
            if (first[letter] > pieceEnd) {
                if (pieceEnd >= 0) {
                    sizes.add(pieceEnd - pieceStart + 1);
                }
                pieceStart = first[letter];
            }
            pieceEnd = Math.max(pieceEnd, last[letter]);
        }
        sizes.add(pieceEnd - pieceStart + 1);
        return sizes.stream().mapToInt(Integer::intValue).toArray();
    }
}
