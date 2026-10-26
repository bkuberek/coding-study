import java.util.*;

public class Solution {
    public int ladderLength(String beginWord, String endWord, String[] wordList) {
        if (!Arrays.asList(wordList).contains(endWord)) {
            return 0;
        }
        List<String> unvisited = new ArrayList<>();
        for (String word : wordList) {
            if (!word.equals(beginWord)) {
                unvisited.add(word);
            }
        }
        Queue<String> queue = new ArrayDeque<>();
        queue.add(beginWord);
        for (int words = 1; !queue.isEmpty(); words++) {
            for (int i = queue.size(); i > 0; i--) {
                String word = queue.poll();
                if (word.equals(endWord)) {
                    return words;
                }
                // Compare against every word not reached yet; the neighbors leave the list.
                List<String> remaining = new ArrayList<>();
                for (String candidate : unvisited) {
                    if (oneApart(word, candidate)) {
                        queue.add(candidate);
                    } else {
                        remaining.add(candidate);
                    }
                }
                unvisited = remaining;
            }
        }
        return 0;
    }

    private static boolean oneApart(String first, String second) {
        int differences = 0;
        for (int i = 0; i < first.length(); i++) {
            if (first.charAt(i) != second.charAt(i) && ++differences > 1) {
                return false;
            }
        }
        return differences == 1;
    }
}
