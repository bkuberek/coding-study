import java.util.*;

public class Solution {
    public int ladderLength(String beginWord, String endWord, String[] wordList) {
        Set<String> available = new HashSet<>(Arrays.asList(wordList));
        if (!available.contains(endWord)) {
            return 0;
        }
        available.remove(beginWord);
        available.remove(endWord);
        // Two frontiers grow toward each other; words counts the ladder length covered so far.
        Set<String> near = new HashSet<>(List.of(beginWord));
        Set<String> far = new HashSet<>(List.of(endWord));
        int words = 1;
        while (!near.isEmpty() && !far.isEmpty()) {
            if (near.size() > far.size()) {
                // Always expand the smaller frontier.
                Set<String> swap = near;
                near = far;
                far = swap;
            }
            words++;
            Set<String> next = new HashSet<>();
            for (String word : near) {
                char[] letters = word.toCharArray();
                for (int position = 0; position < letters.length; position++) {
                    char original = letters[position];
                    for (char letter = 'a'; letter <= 'z'; letter++) {
                        letters[position] = letter;
                        String candidate = new String(letters);
                        if (far.contains(candidate)) {
                            return words;
                        }
                        if (available.remove(candidate)) {
                            next.add(candidate);
                        }
                    }
                    letters[position] = original;
                }
            }
            near = next;
        }
        return 0;
    }
}
