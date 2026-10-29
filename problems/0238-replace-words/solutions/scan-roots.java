import java.util.*;

public class Solution {
    public String replaceWords(String[] dictionary, String sentence) {
        StringBuilder result = new StringBuilder();
        for (String word : sentence.split(" ")) {
            String best = word;
            for (String root : dictionary) {
                if (root.length() < best.length() && word.startsWith(root)) {
                    best = root;
                }
            }
            if (result.length() > 0) {
                result.append(' ');
            }
            result.append(best);
        }
        return result.toString();
    }
}
