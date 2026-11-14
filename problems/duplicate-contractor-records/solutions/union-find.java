import java.util.*;

public class Solution {
    private static final Set<String> LEGAL_FORMS = Set.of("co", "company", "corp", "inc", "incorporated", "llc", "ltd");
    private static final int TAX_ID_DIGITS = 9;

    public List<List<Integer>> duplicateGroups(String[] names, String[] taxIds) {
        int count = names.length;
        int[] parent = new int[count];
        for (int record = 0; record < count; record++) {
            parent[record] = record;
        }
        // Two key spaces: a name never matches a tax id.
        Map<String, Integer> firstWithName = new HashMap<>();
        Map<String, Integer> firstWithTaxId = new HashMap<>();
        for (int record = 0; record < count; record++) {
            link(parent, firstWithName, normalizeName(names[record]), record);
            link(parent, firstWithTaxId, normalizeTaxId(taxIds[record]), record);
        }
        Map<Integer, List<Integer>> groups = new LinkedHashMap<>(); // insertion order = smallest index first
        for (int record = 0; record < count; record++) {
            groups.computeIfAbsent(find(parent, record), root -> new ArrayList<>()).add(record);
        }
        List<List<Integer>> result = new ArrayList<>();
        for (List<Integer> members : groups.values()) {
            if (members.size() > 1) {
                result.add(members);
            }
        }
        return result;
    }

    private static void link(int[] parent, Map<String, Integer> firstWithKey, String key, int record) {
        if (key.isEmpty()) {
            return; // an empty key matches nothing
        }
        Integer first = firstWithKey.putIfAbsent(key, record);
        if (first != null) {
            parent[find(parent, record)] = find(parent, first);
        }
    }

    private static int find(int[] parent, int record) {
        while (parent[record] != record) {
            parent[record] = parent[parent[record]]; // path halving
            record = parent[record];
        }
        return record;
    }

    private static String normalizeName(String name) {
        // Locale.ROOT: the default locale could turn I into a dotless i.
        List<String> words = new ArrayList<>();
        for (String word : name.toLowerCase(Locale.ROOT).split("[^a-z0-9]+")) {
            if (!word.isEmpty()) {
                words.add(word);
            }
        }
        while (!words.isEmpty() && LEGAL_FORMS.contains(words.get(words.size() - 1))) {
            words.remove(words.size() - 1);
        }
        return String.join(" ", words);
    }

    private static String normalizeTaxId(String taxId) {
        StringBuilder digits = new StringBuilder();
        for (char c : taxId.toCharArray()) {
            if (c >= '0' && c <= '9') {
                digits.append(c);
            }
        }
        return digits.length() == TAX_ID_DIGITS ? digits.toString() : "";
    }
}
