import java.util.*;

/**
 * Modules keep the imports as written. The first question after a change resolves every import
 * to the longest declared module that is the import or a dotted prefix of it, and keeps one
 * sorted list of targets per module, so every walk visits neighbours in name order.
 *
 * <p>A breadth-first walk from a sorted list of starts, over sorted neighbours, reaches each
 * module first along the shortest chain that is smallest in name order, so one walk per source
 * name answers every pair of a contract that starts there. Cycles are the strongly connected
 * components, found with two depth-first passes over the graph and its reverse.
 */
public class ArchitectureChecker {
    private static final class Contract {
        final List<String[]> pairs;
        boolean direct = false;
        final Set<List<String>> ignores = new HashSet<>();
        final Map<List<String>, String> exceptions = new HashMap<>();

        Contract(List<String[]> pairs) {
            this.pairs = pairs;
        }
    }

    private record Walk(List<String> order, Map<String, String> parent) {}

    private record Violation(List<String> key, List<String> chain) {}

    private final Map<String, List<String>> imports = new HashMap<>();
    private Map<String, List<String>> graph = null;
    private final Map<String, Contract> contracts = new HashMap<>();
    private List<Integer> version = new ArrayList<>();
    private Set<List<String>> baseline = new HashSet<>();

    // Level 1
    public boolean addModule(String name, List<String> imports) {
        boolean isNew = !this.imports.containsKey(name);
        this.imports.put(name, new ArrayList<>(imports));
        graph = null;
        return isNew;
    }

    public List<List<String>> unknownImports() {
        Set<List<String>> rows = new HashSet<>();
        for (Map.Entry<String, List<String>> entry : imports.entrySet()) {
            for (String text : entry.getValue()) {
                if (resolve(text) == null) rows.add(List.of(entry.getKey(), text));
            }
        }
        return sortedRows(rows);
    }

    public List<String> dependencies(String name) {
        Map<String, List<String>> edges = edges();
        TreeSet<String> found = new TreeSet<>();
        for (String module : members(name)) {
            for (String target : edges.get(module)) {
                if (!inside(target, name)) found.add(target);
            }
        }
        return new ArrayList<>(found);
    }

    public List<String> transitiveDependencies(String name) {
        Walk walk = walk(members(name), null);
        Map<String, Integer> depth = new HashMap<>();
        List<String> reached = new ArrayList<>();
        for (String module : walk.order()) {
            String above = walk.parent().get(module);
            depth.put(module, above == null ? 0 : depth.get(above) + 1);
            if (!inside(module, name)) reached.add(module);
        }
        reached.sort(Comparator.comparing((String module) -> depth.get(module))
                .thenComparing(Comparator.naturalOrder()));
        return reached;
    }

    // Level 2
    public List<List<String>> cycles(int depth) {
        Map<String, Set<String>> adjacency = new HashMap<>();
        for (Map.Entry<String, List<String>> entry : edges().entrySet()) {
            String group = groupOf(entry.getKey(), depth);
            Set<String> out = adjacency.computeIfAbsent(group, key -> new TreeSet<>());
            for (String target : entry.getValue()) {
                String other = groupOf(target, depth);
                if (!other.equals(group)) out.add(other);
            }
        }
        List<List<String>> found = new ArrayList<>();
        for (List<String> part : components(adjacency)) {
            if (part.size() > 1) {
                Collections.sort(part);
                found.add(part);
            }
        }
        found.sort(ArchitectureChecker::compareRows);
        return found;
    }

    public List<String> cycleChain(String name) {
        if (!imports.containsKey(name)) return new ArrayList<>();
        Map<String, List<String>> edges = edges();
        Walk walk = walk(List.of(name), null);
        for (String module : walk.order()) {
            if (edges.get(module).contains(name)) {
                List<String> chain = chainOf(module, walk.parent());
                chain.add(name);
                return chain;
            }
        }
        return new ArrayList<>();
    }

    // Level 3
    public boolean addLayers(String contract, List<String> layers) {
        List<String[]> pairs = new ArrayList<>();
        for (int low = 0; low < layers.size(); low++) {
            for (int high = 0; high < low; high++) {
                pairs.add(new String[] {layers.get(low), layers.get(high)});
            }
        }
        return addContract(contract, pairs);
    }

    public boolean addForbidden(String contract, String source, String target) {
        List<String[]> pairs = new ArrayList<>();
        pairs.add(new String[] {source, target});
        return addContract(contract, pairs);
    }

    public boolean addIndependence(String contract, List<String> names) {
        List<String[]> pairs = new ArrayList<>();
        for (String first : names) {
            for (String second : names) {
                if (!first.equals(second)) pairs.add(new String[] {first, second});
            }
        }
        return addContract(contract, pairs);
    }

    public List<List<String>> check() {
        List<List<String>> rows = new ArrayList<>();
        for (Violation violation : violations()) {
            List<String> row = new ArrayList<>(violation.key());
            row.addAll(violation.chain());
            rows.add(row);
        }
        return rows;
    }

    // Level 4
    public boolean ignore(String contract, String importer, String imported) {
        Contract rules = contracts.get(contract);
        if (rules == null) return false;
        return rules.ignores.add(List.of(importer, imported));
    }

    public boolean allow(String contract, String importer, String imported, String until) {
        Contract rules = contracts.get(contract);
        if (rules == null) return false;
        List<String> key = List.of(importer, imported);
        String old = rules.exceptions.get(key);
        if (old != null && compareVersions(versionKey(old), versionKey(until)) == 0) return false;
        rules.exceptions.put(key, until);
        return true;
    }

    public List<List<String>> setVersion(String version) {
        this.version = versionKey(version);
        List<List<String>> rows = new ArrayList<>();
        for (Map.Entry<String, Contract> entry : contracts.entrySet()) {
            for (Map.Entry<List<String>, String> exception : entry.getValue().exceptions.entrySet()) {
                String until = exception.getValue();
                if (compareVersions(versionKey(until), this.version) <= 0) {
                    List<String> pair = exception.getKey();
                    rows.add(List.of(entry.getKey(), pair.get(0), pair.get(1), until));
                }
            }
        }
        return sortedRows(rows);
    }

    public boolean setMode(String contract, String mode) {
        Contract rules = contracts.get(contract);
        boolean direct = mode.equals("direct");
        if (rules == null || rules.direct == direct) return false;
        rules.direct = direct;
        return true;
    }

    public int setBaseline(List<List<String>> entries) {
        baseline = new HashSet<>();
        for (List<String> entry : entries) baseline.add(List.copyOf(entry.subList(0, 3)));
        return baseline.size();
    }

    public List<List<String>> ratchet() {
        List<Violation> current = violations();
        Set<List<String>> broken = new HashSet<>();
        List<List<String>> rows = new ArrayList<>();
        for (Violation violation : current) {
            broken.add(violation.key());
            if (!baseline.contains(violation.key())) {
                List<String> row = new ArrayList<>();
                row.add("new");
                row.addAll(violation.key());
                row.addAll(violation.chain());
                rows.add(row);
            }
        }
        List<List<String>> fixed = new ArrayList<>();
        for (List<String> entry : baseline) {
            if (!broken.contains(entry)) fixed.add(entry);
        }
        fixed.sort(ArchitectureChecker::compareRows);
        for (List<String> entry : fixed) {
            baseline.remove(entry);
            List<String> row = new ArrayList<>();
            row.add("fixed");
            row.addAll(entry);
            rows.add(row);
        }
        return rows;
    }

    // Helpers
    private String resolve(String text) {
        String name = text;
        while (!imports.containsKey(name)) {
            int cut = name.lastIndexOf('.');
            if (cut < 0) return null;
            name = name.substring(0, cut);
        }
        return name;
    }

    private Map<String, List<String>> edges() {
        if (graph == null) {
            Map<String, List<String>> built = new HashMap<>();
            for (Map.Entry<String, List<String>> entry : imports.entrySet()) {
                TreeSet<String> targets = new TreeSet<>();
                for (String text : entry.getValue()) {
                    String target = resolve(text);
                    if (target != null && !target.equals(entry.getKey())) targets.add(target);
                }
                built.put(entry.getKey(), new ArrayList<>(targets));
            }
            graph = built;
        }
        return graph;
    }

    private List<String> members(String name) {
        List<String> found = new ArrayList<>();
        for (String module : imports.keySet()) {
            if (inside(module, name)) found.add(module);
        }
        Collections.sort(found);
        return found;
    }

    /** Breadth-first from the sorted starts over sorted neighbours. */
    private Walk walk(List<String> starts, Contract rules) {
        Map<String, List<String>> edges = edges();
        Map<String, String> parent = new HashMap<>();
        List<String> order = new ArrayList<>(starts);
        ArrayDeque<String> queue = new ArrayDeque<>(starts);
        for (String start : starts) parent.put(start, null);
        while (!queue.isEmpty()) {
            String module = queue.poll();
            for (String target : edges.get(module)) {
                if (!parent.containsKey(target) && !skipped(rules, module, target)) {
                    parent.put(target, module);
                    order.add(target);
                    queue.add(target);
                }
            }
        }
        return new Walk(order, parent);
    }

    private boolean addContract(String contract, List<String[]> pairs) {
        if (contracts.containsKey(contract)) return false;
        contracts.put(contract, new Contract(pairs));
        return true;
    }

    private boolean skipped(Contract rules, String importer, String imported) {
        if (rules == null) return false;
        for (List<String> rule : rules.ignores) {
            if (inside(importer, rule.get(0)) && inside(imported, rule.get(1))) return true;
        }
        for (Map.Entry<List<String>, String> exception : rules.exceptions.entrySet()) {
            boolean live = compareVersions(version, versionKey(exception.getValue())) < 0;
            List<String> rule = exception.getKey();
            if (live && inside(importer, rule.get(0)) && inside(imported, rule.get(1))) return true;
        }
        return false;
    }

    private List<Violation> violations() {
        List<Violation> found = new ArrayList<>();
        for (String name : new TreeSet<>(contracts.keySet())) {
            Contract rules = contracts.get(name);
            TreeSet<String> sources = new TreeSet<>();
            for (String[] pair : rules.pairs) sources.add(pair[0]);
            for (String source : sources) {
                List<String> targets = new ArrayList<>();
                for (String[] pair : rules.pairs) {
                    if (pair[0].equals(source)) targets.add(pair[1]);
                }
                for (Map.Entry<String, List<String>> hit : chains(rules, source, targets).entrySet()) {
                    found.add(new Violation(List.of(name, source, hit.getKey()), hit.getValue()));
                }
            }
        }
        found.sort((a, b) -> compareRows(a.key(), b.key()));
        return found;
    }

    private Map<String, List<String>> chains(Contract rules, String source, List<String> targets) {
        List<String> starts = members(source);
        Map<String, List<String>> found = new HashMap<>();
        if (rules.direct) {
            for (String target : targets) {
                List<String> pair = firstImport(rules, starts, target);
                if (pair != null) found.put(target, pair);
            }
            return found;
        }
        Walk walk = walk(starts, rules);
        for (String target : targets) {
            for (String module : walk.order()) {
                if (inside(module, target)) {
                    found.put(target, chainOf(module, walk.parent()));
                    break;
                }
            }
        }
        return found;
    }

    /** The starts and their targets are sorted, so the first import found is the smallest. */
    private List<String> firstImport(Contract rules, List<String> starts, String target) {
        Map<String, List<String>> edges = edges();
        for (String module : starts) {
            for (String other : edges.get(module)) {
                if (inside(other, target) && !skipped(rules, module, other)) {
                    return List.of(module, other);
                }
            }
        }
        return null;
    }

    private static boolean inside(String module, String name) {
        return module.equals(name) || module.startsWith(name + ".");
    }

    private static String groupOf(String module, int depth) {
        if (depth == 0) return module;
        String[] parts = module.split("\\.");
        return String.join(".", Arrays.copyOfRange(parts, 0, Math.min(depth, parts.length)));
    }

    private static List<String> chainOf(String module, Map<String, String> parent) {
        List<String> chain = new ArrayList<>();
        for (String step = module; step != null; step = parent.get(step)) chain.add(step);
        Collections.reverse(chain);
        return chain;
    }

    private static List<Integer> versionKey(String text) {
        List<Integer> parts = new ArrayList<>();
        for (String part : text.split("\\.")) parts.add(Integer.parseInt(part));
        while (!parts.isEmpty() && parts.get(parts.size() - 1) == 0) parts.remove(parts.size() - 1);
        return parts;
    }

    private static int compareVersions(List<Integer> a, List<Integer> b) {
        for (int i = 0; i < Math.min(a.size(), b.size()); i++) {
            int order = Integer.compare(a.get(i), b.get(i));
            if (order != 0) return order;
        }
        return Integer.compare(a.size(), b.size());
    }

    private static int compareRows(List<String> a, List<String> b) {
        for (int i = 0; i < Math.min(a.size(), b.size()); i++) {
            int order = a.get(i).compareTo(b.get(i));
            if (order != 0) return order;
        }
        return Integer.compare(a.size(), b.size());
    }

    private static List<List<String>> sortedRows(Collection<List<String>> rows) {
        List<List<String>> sorted = new ArrayList<>(rows);
        sorted.sort(ArchitectureChecker::compareRows);
        return sorted;
    }

    /** Two depth-first passes: finishing order on the graph, then components on its reverse. */
    private static List<List<String>> components(Map<String, Set<String>> adjacency) {
        List<String> nodes = new ArrayList<>(adjacency.keySet());
        Collections.sort(nodes);
        Map<String, List<String>> forward = new HashMap<>();
        Map<String, List<String>> reverse = new HashMap<>();
        for (String node : nodes) {
            forward.put(node, new ArrayList<>(adjacency.get(node)));
            reverse.put(node, new ArrayList<>());
        }
        for (String node : nodes) {
            for (String target : forward.get(node)) reverse.get(target).add(node);
        }
        List<String> finished = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        for (String root : nodes) {
            if (!seen.add(root)) continue;
            ArrayDeque<String> stack = new ArrayDeque<>();
            ArrayDeque<Integer> next = new ArrayDeque<>();
            stack.push(root);
            next.push(0);
            while (!stack.isEmpty()) {
                String node = stack.peek();
                int index = next.pop();
                List<String> targets = forward.get(node);
                if (index < targets.size()) {
                    next.push(index + 1);
                    String target = targets.get(index);
                    if (seen.add(target)) {
                        stack.push(target);
                        next.push(0);
                    }
                } else {
                    stack.pop();
                    finished.add(node);
                }
            }
        }
        Set<String> assigned = new HashSet<>();
        List<List<String>> parts = new ArrayList<>();
        for (int i = finished.size() - 1; i >= 0; i--) {
            String root = finished.get(i);
            if (!assigned.add(root)) continue;
            List<String> part = new ArrayList<>();
            ArrayDeque<String> stack = new ArrayDeque<>();
            stack.push(root);
            while (!stack.isEmpty()) {
                String node = stack.pop();
                part.add(node);
                for (String source : reverse.get(node)) {
                    if (assigned.add(source)) stack.push(source);
                }
            }
            parts.add(part);
        }
        return parts;
    }
}
