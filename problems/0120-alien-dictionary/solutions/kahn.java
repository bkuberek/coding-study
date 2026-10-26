import java.util.*;

public class Solution {
    private static final int LETTERS = 26;

    public String alienOrder(String[] words) {
        boolean[] present = new boolean[LETTERS];
        for (String word : words) {
            for (char letter : word.toCharArray()) {
                present[letter - 'a'] = true;
            }
        }
        // before[x][y]: letter x must come before letter y. A matrix dedupes repeated rules.
        boolean[][] before = new boolean[LETTERS][LETTERS];
        for (int i = 0; i + 1 < words.length; i++) {
            String first = words[i];
            String second = words[i + 1];
            int shorter = Math.min(first.length(), second.length());
            int k = 0;
            while (k < shorter && first.charAt(k) == second.charAt(k)) {
                k++;
            }
            if (k < shorter) {
                before[first.charAt(k) - 'a'][second.charAt(k) - 'a'] = true;
            } else if (first.length() > second.length()) {
                return ""; // a word placed before its own proper prefix
            }
        }
        int[] waiting = new int[LETTERS];
        for (int x = 0; x < LETTERS; x++) {
            for (int y = 0; y < LETTERS; y++) {
                if (before[x][y]) {
                    waiting[y]++;
                }
            }
        }
        ArrayDeque<Integer> ready = new ArrayDeque<>();
        int letterCount = 0;
        for (int x = 0; x < LETTERS; x++) {
            if (present[x]) {
                letterCount++;
                if (waiting[x] == 0) {
                    ready.add(x);
                }
            }
        }
        StringBuilder order = new StringBuilder();
        while (!ready.isEmpty()) {
            int x = ready.poll();
            order.append((char) ('a' + x));
            for (int y = 0; y < LETTERS; y++) {
                if (before[x][y] && --waiting[y] == 0) {
                    ready.add(y);
                }
            }
        }
        return order.length() == letterCount ? order.toString() : "";
    }
}
