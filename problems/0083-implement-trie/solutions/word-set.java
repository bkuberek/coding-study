import java.util.*;

public class Trie {
    private final Set<String> words = new HashSet<>();

    public Trie() {
    }

    public void insert(String word) {
        words.add(word);
    }

    public boolean search(String word) {
        return words.contains(word);
    }

    public boolean startsWith(String prefix) {
        for (String word : words) {
            if (word.startsWith(prefix)) {
                return true;
            }
        }
        return false;
    }
}
