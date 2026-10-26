import java.util.*;

public class Solution {
    private static final class DisjointSets {
        private final int[] parent;
        private final int[] size; // size[r]: number of accounts in the tree rooted at r

        DisjointSets(int count) {
            parent = new int[count];
            size = new int[count];
            for (int x = 0; x < count; x++) {
                parent[x] = x;
                size[x] = 1;
            }
        }

        int find(int x) {
            int root = x;
            while (parent[root] != root) {
                root = parent[root];
            }
            while (parent[x] != root) { // path compression: point the whole path at the root
                int next = parent[x];
                parent[x] = root;
                x = next;
            }
            return root;
        }

        void union(int a, int b) {
            int rootA = find(a);
            int rootB = find(b);
            if (rootA == rootB) {
                return;
            }
            if (size[rootA] < size[rootB]) {
                int held = rootA;
                rootA = rootB;
                rootB = held;
            }
            parent[rootB] = rootA; // union by size: the smaller tree goes under the larger
            size[rootA] += size[rootB];
        }
    }

    public List<List<String>> accountsMerge(List<List<String>> accounts) {
        DisjointSets sets = new DisjointSets(accounts.size());
        Map<String, Integer> firstOwner = new HashMap<>(); // address -> first account that listed it
        for (int i = 0; i < accounts.size(); i++) {
            List<String> account = accounts.get(i);
            for (String address : account.subList(1, account.size())) {
                Integer owner = firstOwner.putIfAbsent(address, i);
                if (owner != null) {
                    sets.union(owner, i);
                }
            }
        }
        Map<Integer, TreeSet<String>> addressesByRoot = new HashMap<>();
        for (int i = 0; i < accounts.size(); i++) {
            List<String> account = accounts.get(i);
            addressesByRoot.computeIfAbsent(sets.find(i), unused -> new TreeSet<>())
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
}
