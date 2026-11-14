import java.util.*;
import java.util.function.Predicate;

/**
 * Columns are nodes named dataset.column, and each lineage edge points from an input column to the
 * column computed from it. Two adjacency maps, forward and backward, answer every walk: a
 * breadth-first search gives distances for the ordered queries, a filter on the edge's usage
 * restricts a walk to the edges a change or a label travels along, and Kosaraju's two passes group
 * the columns that sit on a cycle.
 */
public class LineageGraph {
    private static final Set<String> USAGES = Set.of("identity", "transform", "aggregate", "filter");
    private static final Set<String> MASKABLE = Set.of("transform", "aggregate");

    private record Edge(String source, String target, String usage, boolean masking) {
        boolean carriesValue() {
            return !usage.equals("filter") && !masking;
        }
    }

    private static final Comparator<List<String>> ROWS = (a, b) -> {
        for (int at = 0; at < Math.min(a.size(), b.size()); at++) {
            int order = a.get(at).compareTo(b.get(at));
            if (order != 0) {
                return order;
            }
        }
        return Integer.compare(a.size(), b.size());
    };

    private final Map<String, List<String>> columns = new HashMap<>();
    private final List<Edge> edges = new ArrayList<>();
    private final Map<String, List<Edge>> forward = new HashMap<>();
    private final Map<String, List<Edge>> backward = new HashMap<>();
    private final Map<String, Set<String>> labels = new HashMap<>();
    private final Set<String> published = new HashSet<>();

    public LineageGraph() {
    }

    // Level 1
    public boolean addDataset(String name, List<String> columns, List<List<String>> edges) {
        if (this.columns.containsKey(name) || !isName(name) || new HashSet<>(columns).size() != columns.size()) {
            return false;
        }
        for (String column : columns) {
            if (!isName(column)) {
                return false;
            }
        }
        Set<List<String>> pairs = new HashSet<>();
        List<Edge> parsed = new ArrayList<>();
        for (List<String> edge : edges) {
            if (edge.size() < 3 || edge.size() > 4 || !columns.contains(edge.get(0)) || !isColumnRef(edge.get(1))) {
                return false;
            }
            String usage = edge.get(2);
            boolean masking = edge.size() == 4;
            if (!USAGES.contains(usage) || (masking && (!edge.get(3).equals("masking") || !MASKABLE.contains(usage)))) {
                return false;
            }
            if (!pairs.add(List.of(edge.get(0), edge.get(1)))) {
                return false;
            }
            parsed.add(new Edge(edge.get(1), name + "." + edge.get(0), usage, masking));
        }
        this.columns.put(name, new ArrayList<>(columns));
        for (Edge edge : parsed) {
            this.edges.add(edge);
            forward.computeIfAbsent(edge.source(), key -> new ArrayList<>()).add(edge);
            backward.computeIfAbsent(edge.target(), key -> new ArrayList<>()).add(edge);
        }
        return true;
    }

    public List<List<String>> validate() {
        List<List<String>> issues = new ArrayList<>();
        for (Edge edge : edges) {
            int dot = edge.source().indexOf('.');
            List<String> declared = columns.get(edge.source().substring(0, dot));
            if (declared == null) {
                issues.add(List.of("unknown-dataset", edge.target(), edge.source()));
            } else if (!declared.contains(edge.source().substring(dot + 1))) {
                issues.add(List.of("unknown-column", edge.target(), edge.source()));
            }
        }
        for (List<String> group : cycles()) {
            List<String> issue = new ArrayList<>();
            issue.add("cycle");
            issue.addAll(group);
            issues.add(issue);
        }
        issues.sort(ROWS);
        return issues;
    }

    public List<String> inputsOf(String column) {
        List<String> inputs = new ArrayList<>();
        for (Edge edge : backward.getOrDefault(column, List.of())) {
            inputs.add(edge.source());
        }
        Collections.sort(inputs);
        return inputs;
    }

    // Level 2
    public List<String> upstream(String column) {
        return byDistance(walk(column, false, edge -> true));
    }

    public List<String> downstream(String column) {
        return byDistance(walk(column, true, edge -> true));
    }

    // Level 3
    public List<List<String>> impact(String column, String change) {
        Map<String, Integer> reached = affected(column, change);
        List<List<String>> rows = new ArrayList<>();
        for (String name : byDistance(reached)) {
            rows.add(List.of(name, reached.get(name) == 1 ? "direct" : "derived"));
        }
        return rows;
    }

    public boolean isBreaking(String column, String change) {
        if (!change.equals("retype")) {
            return !affected(column, change).isEmpty();
        }
        for (String name : typed(column).keySet()) {
            for (Edge edge : forward.getOrDefault(name, List.of())) {
                if (!edge.usage().equals("identity")) {
                    return true;
                }
            }
        }
        return false;
    }

    public List<String> impactedDatasets(String column, String change) {
        TreeSet<String> datasets = new TreeSet<>();
        for (String name : affected(column, change).keySet()) {
            datasets.add(name.substring(0, name.indexOf('.')));
        }
        return new ArrayList<>(datasets);
    }

    // Level 4
    public boolean tag(String column, String label) {
        if (!declared(column)) {
            return false;
        }
        return labels.computeIfAbsent(column, key -> new HashSet<>()).add(label);
    }

    public List<String> tagsOf(String column) {
        Map<String, Integer> sources = walk(column, false, Edge::carriesValue);
        sources.put(column, 0);
        TreeSet<String> found = new TreeSet<>();
        for (String name : sources.keySet()) {
            found.addAll(labels.getOrDefault(name, Set.of()));
        }
        return new ArrayList<>(found);
    }

    public boolean publish(String dataset) {
        return columns.containsKey(dataset) && published.add(dataset);
    }

    public List<List<String>> exposures(String label) {
        List<List<String>> found = new ArrayList<>();
        for (Map.Entry<String, Set<String>> entry : labels.entrySet()) {
            if (!entry.getValue().contains(label)) {
                continue;
            }
            String source = entry.getKey();
            Map<String, Integer> reached = walk(source, true, Edge::carriesValue);
            reached.put(source, 0);
            for (String name : reached.keySet()) {
                if (published.contains(name.substring(0, name.indexOf('.')))) {
                    found.add(List.of(name, source));
                }
            }
        }
        found.sort(ROWS);
        return found;
    }

    // Helpers
    /** A dataset or column name: 1 to 20 characters from a-z, 0-9 and _. */
    private static boolean isName(String text) {
        if (text.isEmpty() || text.length() > 20) {
            return false;
        }
        for (int at = 0; at < text.length(); at++) {
            char ch = text.charAt(at);
            if (!((ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') || ch == '_')) {
                return false;
            }
        }
        return true;
    }

    private static boolean isColumnRef(String text) {
        int dot = text.indexOf('.');
        return dot >= 0 && isName(text.substring(0, dot)) && isName(text.substring(dot + 1));
    }

    private boolean declared(String column) {
        if (!isColumnRef(column)) {
            return false;
        }
        int dot = column.indexOf('.');
        List<String> declared = columns.get(column.substring(0, dot));
        return declared != null && declared.contains(column.substring(dot + 1));
    }

    /** Breadth-first distances from start along the kept edges; start is in the answer only on a cycle. */
    private Map<String, Integer> walk(String start, boolean ahead, Predicate<Edge> keep) {
        Map<String, Integer> distance = new HashMap<>();
        ArrayDeque<String> queue = new ArrayDeque<>();
        Map<String, Integer> steps = new HashMap<>();
        queue.add(start);
        steps.put(start, 0);
        while (!queue.isEmpty()) {
            String node = queue.poll();
            int here = steps.get(node);
            for (Edge edge : (ahead ? forward : backward).getOrDefault(node, List.of())) {
                String next = ahead ? edge.target() : edge.source();
                if (keep.test(edge) && !distance.containsKey(next)) {
                    distance.put(next, here + 1);
                    steps.put(next, here + 1);
                    queue.add(next);
                }
            }
        }
        return distance;
    }

    private Map<String, Integer> typed(String column) {
        Map<String, Integer> typed = walk(column, true, edge -> edge.usage().equals("identity"));
        typed.put(column, 0);
        return typed;
    }

    private Map<String, Integer> affected(String column, String change) {
        if (change.equals("drop")) {
            return walk(column, true, edge -> true);
        }
        Map<String, Integer> affected = new HashMap<>();
        if (change.equals("rename")) {
            for (Edge edge : forward.getOrDefault(column, List.of())) {
                affected.put(edge.target(), 1);
            }
            return affected;
        }
        for (Map.Entry<String, Integer> entry : typed(column).entrySet()) {
            for (Edge edge : forward.getOrDefault(entry.getKey(), List.of())) {
                affected.merge(edge.target(), entry.getValue() + 1, Math::min);
            }
        }
        return affected;
    }

    private static List<String> byDistance(Map<String, Integer> distance) {
        List<String> names = new ArrayList<>(distance.keySet());
        names.sort(Comparator.comparing((String name) -> distance.get(name)).thenComparing(name -> name));
        return names;
    }

    /** Strongly connected groups that hold a cycle, by Kosaraju's two passes. */
    private List<List<String>> cycles() {
        TreeSet<String> nodes = new TreeSet<>();
        Set<String> selfLoops = new HashSet<>();
        for (Edge edge : edges) {
            nodes.add(edge.source());
            nodes.add(edge.target());
            if (edge.source().equals(edge.target())) {
                selfLoops.add(edge.source());
            }
        }
        List<String> finished = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        for (String root : nodes) {
            if (!seen.add(root)) {
                continue;
            }
            ArrayDeque<String> stack = new ArrayDeque<>();
            ArrayDeque<Integer> positions = new ArrayDeque<>();
            stack.push(root);
            positions.push(0);
            while (!stack.isEmpty()) {
                String node = stack.peek();
                int at = positions.pop();
                List<Edge> out = forward.getOrDefault(node, List.of());
                if (at == out.size()) {
                    stack.pop();
                    finished.add(node);
                    continue;
                }
                positions.push(at + 1);
                String next = out.get(at).target();
                if (seen.add(next)) {
                    stack.push(next);
                    positions.push(0);
                }
            }
        }
        Set<String> grouped = new HashSet<>();
        List<List<String>> groups = new ArrayList<>();
        for (int at = finished.size() - 1; at >= 0; at--) {
            String root = finished.get(at);
            if (!grouped.add(root)) {
                continue;
            }
            List<String> members = new ArrayList<>(List.of(root));
            ArrayDeque<String> pending = new ArrayDeque<>(List.of(root));
            while (!pending.isEmpty()) {
                for (Edge edge : backward.getOrDefault(pending.pop(), List.of())) {
                    if (grouped.add(edge.source())) {
                        members.add(edge.source());
                        pending.push(edge.source());
                    }
                }
            }
            Collections.sort(members);
            if (members.size() > 1 || selfLoops.contains(root)) {
                groups.add(members);
            }
        }
        return groups;
    }
}
