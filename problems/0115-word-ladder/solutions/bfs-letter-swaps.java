import java.util.*;

public class Solution {
    public int ladderLength(String beginWord, String endWord, String[] wordList) {
        // Words still available; a word leaves the set the moment it is reached.
        Set<String> available = new HashSet<>(Arrays.asList(wordList));
        if (!available.contains(endWord)) {
            return 0;
        }
        available.remove(beginWord);
        Queue<String> queue = new ArrayDeque<>();
        queue.add(beginWord);
        for (int words = 1; !queue.isEmpty(); words++) {
            for (int i = queue.size(); i > 0; i--) {
                String word = queue.poll();
                if (word.equals(endWord)) {
                    return words;
                }
                char[] letters = word.toCharArray();
                for (int position = 0; position < letters.length; position++) {
                    char original = letters[position];
                    for (char letter = 'a'; letter <= 'z'; letter++) {
                        letters[position] = letter;
                        String candidate = new String(letters);
                        if (available.remove(candidate)) {
                            queue.add(candidate);
                        }
                    }
                    letters[position] = original;
                }
            }
        }
        return 0;
    }
}
