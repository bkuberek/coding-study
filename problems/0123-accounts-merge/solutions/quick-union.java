import java.util.*;

public class Solution {
    public List<List<String>> accountsMerge(List<List<String>> accounts) {
        int[] parent = new int[accounts.size()]; // parent[x] == x marks a root
        for (int x = 0; x < parent.length; x++) {
            parent[x] = x;
        }
        Map<String, Integer> firstOwner = new HashMap<>(); // address -> first account that listed it
        for (int i = 0; i < accounts.size(); i++) {
            List<String> account = accounts.get(i);
            for (String address : account.subList(1, account.size())) {
                Integer owner = firstOwner.putIfAbsent(address, i);
                if (owner == null) {
                    continue;
                }
                int rootOwner = find(parent, owner);
                int rootHere = find(parent, i);
                if (rootOwner != rootHere) {
                    parent[rootOwner] = rootHere; // no balancing: trees can grow into long chains
                }
            }
        }
        Map<Integer, TreeSet<String>> addressesByRoot = new HashMap<>();
        for (int i = 0; i < accounts.size(); i++) {
            List<String> account = accounts.get(i);
            addressesByRoot.computeIfAbsent(find(parent, i), unused -> new TreeSet<>())
                    .addAll(account.subList(1, account.size()));
        }
        List<List<String>> merged = new ArrayList<>();
        for (Map.Entry<Integer, TreeSet<String>> entry : addressesByRoot.entrySet()) {
            List<String> person = new ArrayList<>();
            person.add(accounts.get(entry.getKey()).get(0));
            person.addAll(entry.getValue()); // a TreeSet iterates in String.compareTo order
            merged.add(person);
        }
        return merged;
    }

    private static int find(int[] parent, int x) {
        while (parent[x] != x) {
            x = parent[x];
        }
        return x;
    }
}
