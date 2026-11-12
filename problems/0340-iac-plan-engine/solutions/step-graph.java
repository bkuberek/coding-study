import java.util.*;

/**
 * Desired and actual resources are maps of attributes. A plan resolves the references of the
 * desired resources in dependency order, which tells for each resource whether it is created,
 * updated, replaced, left alone or deleted, then turns those actions into steps joined by
 * before-rules and lists the steps in the smallest order by (rank, address) that keeps every rule.
 * Apply walks the same steps, skips those behind a failure, and records the state after each step
 * that succeeds.
 */
public class PlanEngine {
    private static final String UNKNOWN = "<unknown>";
    private static final String FORCES = "forces-replacement";
    private static final String CREATE_FIRST = "create-before-destroy";
    private static final String DELETE_FIRST = "destroy-before-create";

    private static final class Step {
        final String verb;
        final String address;
        final String tag;
        final int rank;
        String mode = "";
        List<List<String>> diff = new ArrayList<>();
        final List<Step> before = new ArrayList<>();
        final List<Step> after = new ArrayList<>();
        int waiting;

        Step(String verb, String address, String tag, int rank) {
            this.verb = verb;
            this.address = address;
            this.tag = tag;
            this.rank = rank;
        }
    }

    private record Built(List<List<String>> errors, List<Step> steps) {}

    private final Map<String, Map<String, String>> desired = new HashMap<>();
    private final Map<String, Map<String, String>> current = new HashMap<>();
    private final Map<String, Set<String>> deps = new HashMap<>();
    private final Map<String, Map<String, String>> old = new HashMap<>();
    private final Map<String, Set<String>> oldDeps = new HashMap<>();
    private final Set<String> forces = new HashSet<>();
    private final Map<String, Set<String>> computedKeys = new HashMap<>();
    private final Set<String> marked = new HashSet<>();

    public PlanEngine() {}

    // Level 1
    public boolean desire(String address, List<List<String>> attributes) {
        return desired.put(address, toMap(attributes)) == null;
    }

    public boolean remove(String address) {
        return desired.remove(address) != null;
    }

    public boolean observe(String address, List<List<String>> attributes) {
        return current.put(address, toMap(attributes)) == null;
    }

    public List<List<String>> plan() {
        Built built = build();
        if (!built.errors().isEmpty()) {
            return built.errors();
        }
        List<List<String>> rows = new ArrayList<>();
        for (Step step : built.steps()) {
            rows.add(step.tag.isEmpty()
                    ? List.of(step.verb, step.address)
                    : List.of(step.verb, step.address, step.tag));
            rows.addAll(step.diff);
        }
        return rows;
    }

    // Level 2
    public boolean observeDependency(String address, String dependsOn) {
        if (!current.containsKey(address) || !current.containsKey(dependsOn)) {
            return false;
        }
        return deps.computeIfAbsent(address, a -> new HashSet<>()).add(dependsOn);
    }

    // Level 3
    public boolean forceReplacement(String resourceType, String key) {
        return forces.add(resourceType + "." + key);
    }

    public boolean computed(String resourceType, String key) {
        return computedKeys.computeIfAbsent(resourceType, t -> new HashSet<>()).add(key);
    }

    public boolean createBeforeDestroy(String address) {
        return marked.add(address);
    }

    // Level 4
    public List<List<String>> apply(List<List<String>> failures, List<List<String>> values) {
        Built built = build();
        if (!built.errors().isEmpty()) {
            return built.errors();
        }
        Set<String> failing = new HashSet<>();
        for (List<String> pair : failures) {
            failing.add(pair.get(0) + " " + pair.get(1));
        }
        Map<String, String> assigned = new HashMap<>();
        for (List<String> row : values) {
            assigned.put(row.get(0) + " " + row.get(1), row.get(2));
        }
        Map<Step, String> status = new HashMap<>();
        List<List<String>> rows = new ArrayList<>();
        for (Step step : built.steps()) {
            String outcome = "ok";
            if (step.before.stream().anyMatch(prior -> !"ok".equals(status.get(prior)))) {
                outcome = "skipped";
            } else if (!step.verb.equals("no-op") && failing.contains(step.verb + " " + step.address)) {
                outcome = "failed";
            } else {
                perform(step, assigned);
            }
            status.put(step, outcome);
            rows.add(List.of(step.verb, step.address, outcome));
        }
        return rows;
    }

    public List<List<String>> state() {
        TreeSet<String> addresses = new TreeSet<>(current.keySet());
        addresses.addAll(old.keySet());
        List<List<String>> rows = new ArrayList<>();
        for (String address : addresses) {
            addStateRow(rows, address, "current", current.get(address));
            addStateRow(rows, address, "old", old.get(address));
        }
        return rows;
    }

    private static void addStateRow(
            List<List<String>> rows, String address, String role, Map<String, String> attributes) {
        if (attributes == null) {
            return;
        }
        List<String> row = new ArrayList<>(List.of(address, role));
        for (String key : new TreeSet<>(attributes.keySet())) {
            row.add(key);
            row.add(attributes.get(key));
        }
        rows.add(row);
    }

    // Planning
    private static Map<String, String> toMap(List<List<String>> attributes) {
        Map<String, String> map = new HashMap<>();
        for (List<String> pair : attributes) {
            map.put(pair.get(0), pair.get(1));
        }
        return map;
    }

    /** The target address and key of a {@code ${type.name.key}} value, or null. */
    private static String[] reference(String value) {
        if (!value.startsWith("${") || !value.endsWith("}")) {
            return null;
        }
        String[] parts = value.substring(2, value.length() - 1).split("\\.");
        return new String[] {parts[0] + "." + parts[1], parts[2]};
    }

    private static String kindOf(String address) {
        return address.substring(0, address.indexOf('.'));
    }

    private boolean isComputed(String address, String key) {
        return computedKeys.getOrDefault(kindOf(address), Set.of()).contains(key);
    }

    private List<String> computedOf(String address) {
        return new ArrayList<>(new TreeSet<>(computedKeys.getOrDefault(kindOf(address), Set.of())));
    }

    private static List<List<String>> removed(Map<String, String> attributes) {
        List<List<String>> rows = new ArrayList<>();
        for (String key : new TreeSet<>(attributes.keySet())) {
            rows.add(List.of("-", key, attributes.get(key)));
        }
        return rows;
    }

    private static void sortByKey(List<List<String>> rows) {
        rows.sort(Comparator.comparing(row -> row.get(1)));
    }

    private static List<List<String>> cycles(Map<String, Set<String>> needs) {
        Map<String, Set<String>> reach = new HashMap<>();
        for (Map.Entry<String, Set<String>> entry : needs.entrySet()) {
            Set<String> seen = new HashSet<>();
            Deque<String> stack = new ArrayDeque<>(entry.getValue());
            while (!stack.isEmpty()) {
                String node = stack.pop();
                if (seen.add(node)) {
                    stack.addAll(needs.get(node));
                }
            }
            reach.put(entry.getKey(), seen);
        }
        TreeMap<String, List<String>> groups = new TreeMap<>();
        for (String node : needs.keySet()) {
            if (reach.get(node).contains(node)) {
                TreeSet<String> group = new TreeSet<>();
                for (String other : reach.get(node)) {
                    if (reach.get(other).contains(node)) {
                        group.add(other);
                    }
                }
                groups.put(group.first(), new ArrayList<>(group));
            }
        }
        List<List<String>> rows = new ArrayList<>();
        for (List<String> group : groups.values()) {
            List<String> row = new ArrayList<>(List.of("error", "cycle"));
            row.addAll(group);
            rows.add(row);
        }
        return rows;
    }

    private static List<String> dependencyOrder(Map<String, Set<String>> needs) {
        Map<String, Integer> waiting = new HashMap<>();
        Map<String, List<String>> users = new HashMap<>();
        for (String address : needs.keySet()) {
            waiting.put(address, needs.get(address).size());
            users.put(address, new ArrayList<>());
        }
        for (Map.Entry<String, Set<String>> entry : needs.entrySet()) {
            for (String target : entry.getValue()) {
                users.get(target).add(entry.getKey());
            }
        }
        PriorityQueue<String> ready = new PriorityQueue<>();
        waiting.forEach((address, count) -> {
            if (count == 0) {
                ready.add(address);
            }
        });
        List<String> order = new ArrayList<>();
        while (!ready.isEmpty()) {
            String address = ready.poll();
            order.add(address);
            for (String user : users.get(address)) {
                if (waiting.merge(user, -1, Integer::sum) == 0) {
                    ready.add(user);
                }
            }
        }
        return order;
    }

    private Set<String> createFirst(Map<String, Set<String>> needs) {
        Set<String> found = new HashSet<>();
        Deque<String> stack = new ArrayDeque<>();
        for (String address : marked) {
            if (desired.containsKey(address)) {
                stack.push(address);
            }
        }
        while (!stack.isEmpty()) {
            String address = stack.pop();
            if (found.add(address)) {
                stack.addAll(needs.get(address));
            }
        }
        return found;
    }

    private Built build() {
        List<List<String>> errors = new ArrayList<>();
        Map<String, Set<String>> needs = new HashMap<>();
        for (String address : desired.keySet()) {
            needs.put(address, new HashSet<>());
        }
        for (String address : new TreeSet<>(desired.keySet())) {
            Map<String, String> attributes = desired.get(address);
            for (String key : new TreeSet<>(attributes.keySet())) {
                String[] target = reference(attributes.get(key));
                if (target == null) {
                    continue;
                }
                Map<String, String> declared = desired.get(target[0]);
                if (declared != null && (declared.containsKey(target[1]) || isComputed(target[0], target[1]))) {
                    needs.get(address).add(target[0]);
                } else {
                    errors.add(List.of("error", "unknown-reference", address, key, target[0] + "." + target[1]));
                }
            }
        }
        errors.addAll(cycles(needs));
        if (!errors.isEmpty()) {
            return new Built(errors, List.of());
        }

        Set<String> early = createFirst(needs);
        Map<String, String> action = new HashMap<>();
        Map<String, Map<String, String>> resolved = new HashMap<>();
        Map<String, Step> applies = new HashMap<>();
        Map<String, Step> deletes = new HashMap<>();
        for (String address : dependencyOrder(needs)) {
            Map<String, String> values = new HashMap<>();
            for (Map.Entry<String, String> entry : desired.get(address).entrySet()) {
                String[] target = reference(entry.getValue());
                if (target == null) {
                    values.put(entry.getKey(), entry.getValue());
                } else if (isComputed(target[0], target[1])) {
                    String kind = action.get(target[0]);
                    boolean replaced = kind.equals("create") || kind.equals("replace");
                    values.put(entry.getKey(), replaced ? UNKNOWN : current.get(target[0]).get(target[1]));
                } else {
                    values.put(entry.getKey(), resolved.get(target[0]).get(target[1]));
                }
            }
            resolved.put(address, values);
            Step step = classify(address, values);
            String kind = step.verb.equals("create") && step.tag.equals("replace") ? "replace" : step.verb;
            action.put(address, kind);
            applies.put(address, step);
            if (kind.equals("replace")) {
                Step half = new Step("delete", address, "replace", 1);
                half.mode = early.contains(address) ? CREATE_FIRST : DELETE_FIRST;
                deletes.put(address, half);
            }
        }
        for (Map.Entry<String, Map<String, String>> entry : current.entrySet()) {
            if (!desired.containsKey(entry.getKey())) {
                Step step = new Step("delete", entry.getKey(), "", 1);
                step.diff = removed(entry.getValue());
                deletes.put(entry.getKey(), step);
            }
        }
        for (Map.Entry<String, Map<String, String>> entry : old.entrySet()) {
            Step step = new Step("delete", entry.getKey(), "old", 1);
            step.diff = removed(entry.getValue());
            deletes.put(entry.getKey(), step);
        }

        for (Map.Entry<String, Set<String>> entry : needs.entrySet()) {
            for (String target : entry.getValue()) {
                link(applies.get(target), applies.get(entry.getKey()));
            }
        }
        for (Step step : deletes.values()) {
            Map<String, Set<String>> held = step.tag.equals("old") ? oldDeps : deps;
            for (String target : held.getOrDefault(step.address, Set.of())) {
                Step gone = deletes.get(target);
                if (gone != null) {
                    link(step, gone);
                }
            }
        }
        for (Step step : applies.values()) {
            if (!current.containsKey(step.address)) {
                continue;
            }
            for (String target : deps.getOrDefault(step.address, Set.of())) {
                Step gone = deletes.get(target);
                if (gone != null && !gone.mode.equals(DELETE_FIRST)) {
                    link(step, gone);
                }
            }
        }
        for (Step step : deletes.values()) {
            if (step.mode.equals(DELETE_FIRST)) {
                link(step, applies.get(step.address));
            } else if (step.mode.equals(CREATE_FIRST)) {
                link(applies.get(step.address), step);
            }
        }
        List<Step> all = new ArrayList<>(applies.values());
        all.addAll(deletes.values());
        return new Built(List.of(), order(all));
    }

    private static void link(Step first, Step second) {
        first.after.add(second);
        second.before.add(first);
    }

    private Step classify(String address, Map<String, String> values) {
        List<String> computed = computedOf(address);
        Map<String, String> existing = current.get(address);
        if (existing == null) {
            Step step = new Step("create", address, "", 0);
            for (Map.Entry<String, String> entry : values.entrySet()) {
                step.diff.add(List.of("+", entry.getKey(), entry.getValue()));
            }
            for (String name : computed) {
                step.diff.add(List.of("+", name, UNKNOWN));
            }
            sortByKey(step.diff);
            return step;
        }
        Map<String, String> actual = new HashMap<>();
        existing.forEach((key, value) -> {
            if (!isComputed(address, key)) {
                actual.put(key, value);
            }
        });
        TreeSet<String> keys = new TreeSet<>(values.keySet());
        keys.addAll(actual.keySet());
        List<List<String>> rows = new ArrayList<>();
        boolean forced = false;
        for (String key : keys) {
            String before = actual.get(key);
            String after = values.get(key);
            if (Objects.equals(before, after)) {
                continue;
            }
            List<String> row = new ArrayList<>();
            if (before == null) {
                row.addAll(List.of("+", key, after));
            } else if (after == null) {
                row.addAll(List.of("-", key, before));
            } else {
                row.addAll(List.of("~", key, before, after));
            }
            if (forces.contains(kindOf(address) + "." + key)) {
                row.add(FORCES);
                forced = true;
            }
            rows.add(row);
        }
        if (rows.isEmpty()) {
            return new Step("no-op", address, "", 0);
        }
        if (!forced) {
            Step step = new Step("update", address, "", 0);
            step.diff = rows;
            return step;
        }
        for (String name : computed) {
            String was = existing.get(name);
            rows.add(was == null ? List.of("+", name, UNKNOWN) : List.of("~", name, was, UNKNOWN));
        }
        sortByKey(rows);
        Step step = new Step("create", address, "replace", 0);
        step.diff = rows;
        return step;
    }

    /** Kahn's algorithm, always taking the smallest ready step by rank, then address. */
    private static List<Step> order(List<Step> steps) {
        PriorityQueue<Step> ready = new PriorityQueue<>(
                Comparator.<Step>comparingInt(step -> step.rank).thenComparing(step -> step.address));
        for (Step step : steps) {
            step.waiting = step.before.size();
            if (step.waiting == 0) {
                ready.add(step);
            }
        }
        List<Step> order = new ArrayList<>();
        while (!ready.isEmpty()) {
            Step step = ready.poll();
            order.add(step);
            for (Step later : step.after) {
                if (--later.waiting == 0) {
                    ready.add(later);
                }
            }
        }
        return order;
    }

    // Applying
    private String live(String address, String key) {
        String value = desired.get(address).get(key);
        String[] target = reference(value);
        if (target == null) {
            return value;
        }
        if (isComputed(target[0], target[1])) {
            return current.get(target[0]).get(target[1]);
        }
        return live(target[0], target[1]);
    }

    private Map<String, String> resolvedNow(String address) {
        Map<String, String> made = new HashMap<>();
        for (String key : desired.get(address).keySet()) {
            made.put(key, live(address, key));
        }
        return made;
    }

    private void perform(Step step, Map<String, String> assigned) {
        String address = step.address;
        Set<String> needs = new HashSet<>();
        if (desired.containsKey(address)) {
            for (String value : desired.get(address).values()) {
                String[] target = reference(value);
                if (target != null) {
                    needs.add(target[0]);
                }
            }
        }
        switch (step.verb) {
            case "create" -> {
                if (step.tag.equals("replace") && current.containsKey(address)) {
                    old.put(address, current.get(address));
                    oldDeps.put(address, deps.getOrDefault(address, new HashSet<>()));
                }
                Map<String, String> made = resolvedNow(address);
                for (String name : computedOf(address)) {
                    made.put(name, assigned.get(address + " " + name));
                }
                current.put(address, made);
                deps.put(address, needs);
            }
            case "update" -> {
                Map<String, String> made = resolvedNow(address);
                current.get(address).forEach((key, value) -> {
                    if (isComputed(address, key)) {
                        made.put(key, value);
                    }
                });
                current.put(address, made);
                deps.put(address, needs);
            }
            case "delete" -> {
                if (step.tag.equals("old") || step.mode.equals(CREATE_FIRST)) {
                    old.remove(address);
                    oldDeps.remove(address);
                } else {
                    current.remove(address);
                    deps.remove(address);
                }
            }
            default -> {}
        }
    }
}
