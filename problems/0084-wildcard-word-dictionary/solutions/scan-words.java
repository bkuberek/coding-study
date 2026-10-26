import java.util.*;

public class WordDictionary {
    private final Map<Integer, Set<String>> byLength = new HashMap<>();

    public WordDictionary() {
    }

    public void addWord(String word) {
        byLength.computeIfAbsent(word.length(), length -> new HashSet<>()).add(word);
    }

    public boolean search(String word) {
        Set<String> candidates = byLength.getOrDefault(word.length(), Set.of());
        if (word.indexOf('.') < 0) {
            return candidates.contains(word);
        }
        for (String candidate : candidates) {
            if (matches(word, candidate)) {
                return true;
            }
        }
        return false;
    }

    private static boolean matches(String pattern, String word) {
        for (int i = 0; i < pattern.length(); i++) {
            char wanted = pattern.charAt(i);
            if (wanted != '.' && wanted != word.charAt(i)) {
                return false;
            }
        }
        return true;
    }
}
