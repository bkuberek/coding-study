import java.util.*;

/**
 * Rows are indexed once by id, then every question is a walk over the index. Nothing here
 * recurses: the outline and the subtree sizes use an explicit stack and a breadth-first order, so
 * a chain of 10^5 managers is as safe as a flat one.
 */
public class OrgChart {
    private List<String> ids = new ArrayList<>();
    private Map<String, String> parents = new HashMap<>();
    private Map<String, String> names = new HashMap<>();
    private Map<String, List<String>> kids = new HashMap<>();
    private List<String> orphanIds = new ArrayList<>();
    private List<String> tops = new ArrayList<>();
    private Set<String> attached = new HashSet<>();
    private Map<String, Integer> sizes = new HashMap<>();
    private List<List<String>> cycleList = new ArrayList<>();

    public OrgChart() {
    }

    // Level 1
    public void load(List<List<String>> rows) {
        ids = new ArrayList<>();
        parents = new HashMap<>();
        names = new HashMap<>();
        kids = new HashMap<>();
        for (List<String> row : rows) {
            ids.add(row.get(0));
            parents.put(row.get(0), row.get(1));
            names.put(row.get(0), row.get(2));
        }
        for (String id : ids) {
            kids.computeIfAbsent(parents.get(id), key -> new ArrayList<>()).add(id);
        }
        orphanIds = new ArrayList<>();
        for (String id : ids) {
            String parent = parents.get(id);
            if (!parent.isEmpty() && !names.containsKey(parent)) {
                orphanIds.add(id);
            }
        }
        Set<String> orphanSet = new HashSet<>(orphanIds);
        tops = new ArrayList<>();
        for (String id : ids) {
            if (parents.get(id).isEmpty() || orphanSet.contains(id)) {
                tops.add(id);
            }
        }
        List<String> order = new ArrayList<>(tops);
        attached = new HashSet<>(order);
        for (int next = 0; next < order.size(); next++) {
            for (String kid : kids.getOrDefault(order.get(next), List.of())) {
                attached.add(kid);
                order.add(kid);
            }
        }
        sizes = new HashMap<>();
        for (String id : order) {
            sizes.put(id, 1);
        }
        for (int at = order.size() - 1; at >= 0; at--) {
            String parent = parents.get(order.get(at));
            Integer parentSize = sizes.get(parent);
            if (parentSize != null) {
                sizes.put(parent, parentSize + sizes.get(order.get(at)));
            }
        }
        cycleList = findCycles();
    }

    public List<String> roots() {
        return new ArrayList<>(kids.getOrDefault("", List.of()));
    }

    public String nameOf(String employee) {
        return names.getOrDefault(employee, "");
    }

    public List<String> children(String employee) {
        return names.containsKey(employee) ? new ArrayList<>(kids.getOrDefault(employee, List.of())) : new ArrayList<>();
    }

    // Level 2
    public List<String> orphans() {
        return new ArrayList<>(orphanIds);
    }

    public List<List<String>> cycles() {
        List<List<String>> copy = new ArrayList<>();
        for (List<String> cycle : cycleList) {
            copy.add(new ArrayList<>(cycle));
        }
        return copy;
    }

    // Level 3
    public List<String> chain(String employee) {
        List<String> path = new ArrayList<>();
        if (!attached.contains(employee)) {
            return path;
        }
        path.add(employee);
        String parent = parents.get(employee);
        while (names.containsKey(parent)) {
            path.add(parent);
            parent = parents.get(parent);
        }
        return path;
    }

    public String lowestCommonManager(String first, String second) {
        Set<String> aboveSecond = new HashSet<>(chain(second));
        for (String manager : chain(first)) {
            if (aboveSecond.contains(manager)) {
                return manager;
            }
        }
        return "";
    }

    // Level 4
    public int subtreeSize(String employee) {
        return sizes.getOrDefault(employee, 0);
    }

    public List<String> outline(String order) {
        List<String> lines = new ArrayList<>();
        Deque<Object[]> stack = new ArrayDeque<>();
        List<String> sortedTops = sorted(tops, order);
        for (int at = sortedTops.size() - 1; at >= 0; at--) {
            stack.push(new Object[] {sortedTops.get(at), 0});
        }
        while (!stack.isEmpty()) {
            Object[] top = stack.pop();
            String current = (String) top[0];
            int depth = (Integer) top[1];
            lines.add("  ".repeat(depth) + names.get(current) + " (" + current + ")");
            List<String> below = sorted(kids.getOrDefault(current, List.of()), order);
            for (int at = below.size() - 1; at >= 0; at--) {
                stack.push(new Object[] {below.get(at), depth + 1});
            }
        }
        return lines;
    }

    private List<String> sorted(List<String> members, String order) {
        List<String> copy = new ArrayList<>(members);
        if (order.equals("name")) {
            copy.sort(Comparator.comparing((String id) -> names.get(id)).thenComparing(id -> id));
        } else if (order.equals("size")) {
            copy.sort(
                    Comparator.comparing((String id) -> -sizes.get(id))
                            .thenComparing(id -> names.get(id))
                            .thenComparing(id -> id));
        }
        return copy;
    }

    private List<List<String>> findCycles() {
        Map<String, Integer> position = new HashMap<>();
        for (int index = 0; index < ids.size(); index++) {
            position.put(ids.get(index), index);
        }
        Set<String> seen = new HashSet<>(attached);
        List<List<String>> found = new ArrayList<>();
        for (String start : ids) {
            List<String> walk = new ArrayList<>();
            String current = start;
            while (!seen.contains(current)) {
                seen.add(current);
                walk.add(current);
                current = parents.get(current);
            }
            int at = walk.indexOf(current);
            if (at >= 0) {
                List<String> cycle = walk.subList(at, walk.size());
                int first = 0;
                for (int k = 1; k < cycle.size(); k++) {
                    if (position.get(cycle.get(k)) < position.get(cycle.get(first))) {
                        first = k;
                    }
                }
                List<String> turned = new ArrayList<>(cycle.subList(first, cycle.size()));
                turned.addAll(cycle.subList(0, first));
                found.add(turned);
            }
        }
        found.sort(Comparator.comparing((List<String> cycle) -> position.get(cycle.get(0))));
        return found;
    }
}
