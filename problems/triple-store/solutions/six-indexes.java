import java.util.*;

/**
 * Every triple ever recorded gets a number and a list of spans, the periods during which it was
 * present. Six hash indexes list the numbers by subject, predicate, object and the three pairs,
 * and one more finds a whole triple, so any pattern with a bound position starts from a short list
 * instead of a scan. Removing a triple only closes its span, so the history stays.
 *
 * <p>A query joins its patterns one at a time, always taking the pattern whose candidate list is
 * shortest under the variables bound so far, and a path is a breadth-first walk with a visited
 * set, so a cycle ends the walk.
 */
public class TripleStore {
    private static final long OPEN = (1L << 53) - 1;
    private static final long CURRENT = OPEN - 1;
    private static final long HUGE = 1_000_000_000_000_000L;
    private static final String SEP = "\u0000";

    private static final class Span {
        final long start;
        long end = OPEN;
        final List<String> names = new ArrayList<>();
        final List<Long> times = new ArrayList<>();

        Span(long start) {
            this.start = start;
        }
    }

    private static final class Found {
        final List<String> row;
        final int[] used;

        Found(List<String> row, int[] used) {
            this.row = row;
            this.used = used;
        }
    }

    private static final class Match {
        final String[] ends;
        final int id;

        Match(String[] ends, int id) {
            this.ends = ends;
            this.id = id;
        }
    }

    private final List<String[]> triples = new ArrayList<>();
    private final List<List<Span>> spans = new ArrayList<>();
    private final Map<String, Integer> exact = new HashMap<>();
    private final Map<String, List<Integer>> byS = new HashMap<>();
    private final Map<String, List<Integer>> byP = new HashMap<>();
    private final Map<String, List<Integer>> byO = new HashMap<>();
    private final Map<String, List<Integer>> bySP = new HashMap<>();
    private final Map<String, List<Integer>> byPO = new HashMap<>();
    private final Map<String, List<Integer>> bySO = new HashMap<>();
    private long now = 0;
    private int live = 0;

    public TripleStore() {
    }

    // Level 1
    public boolean add(String subject, String predicate, String obj) {
        return record(subject, predicate, obj, "", now);
    }

    public boolean remove(String subject, String predicate, String obj) {
        return retract(subject, predicate, obj, now);
    }

    public int size() {
        return live;
    }

    public List<List<String>> match(String subject, String predicate, String obj) {
        List<String[]> found = new ArrayList<>();
        List<Integer> candidates = candidates(term(subject), term(predicate), term(obj));
        for (int id : each(candidates)) {
            if (present(id, CURRENT)) {
                found.add(triples.get(id));
            }
        }
        found.sort((a, b) -> compareRows(Arrays.asList(a), Arrays.asList(b)));
        List<List<String>> answer = new ArrayList<>();
        for (String[] triple : found) {
            answer.add(new ArrayList<>(Arrays.asList(triple)));
        }
        return answer;
    }

    // Level 2 and 3
    public List<List<String>> query(List<List<String>> patterns, List<String> columns) {
        return rows(patterns, columns, CURRENT, false).get(0);
    }

    // Level 4
    public boolean record(String subject, String predicate, String obj, String source, long time) {
        now = time;
        String key = String.join(SEP, subject, predicate, obj);
        Integer id = exact.get(key);
        if (id == null) {
            id = create(subject, predicate, obj, key);
        }
        List<Span> history = spans.get(id);
        if (!history.isEmpty() && history.get(history.size() - 1).end == OPEN) {
            Span last = history.get(history.size() - 1);
            if (!source.isEmpty() && !last.names.contains(source)) {
                last.names.add(source);
                last.times.add(time);
            }
            return false;
        }
        Span span = new Span(time);
        if (!source.isEmpty()) {
            span.names.add(source);
            span.times.add(time);
        }
        history.add(span);
        live++;
        return true;
    }

    public boolean retract(String subject, String predicate, String obj, long time) {
        now = time;
        Integer id = exact.get(String.join(SEP, subject, predicate, obj));
        if (id == null) {
            return false;
        }
        List<Span> history = spans.get(id);
        Span last = history.get(history.size() - 1);
        if (last.end != OPEN) {
            return false;
        }
        last.end = time;
        live--;
        return true;
    }

    public List<List<String>> queryAsOf(List<List<String>> patterns, List<String> columns, long time) {
        return rows(patterns, columns, time, false).get(0);
    }

    public List<List<String>> sourcesAsOf(List<List<String>> patterns, List<String> columns, long time) {
        return rows(patterns, columns, time, true).get(1);
    }

    // Storage
    private int create(String subject, String predicate, String obj, String key) {
        int id = triples.size();
        triples.add(new String[] {subject, predicate, obj});
        spans.add(new ArrayList<>());
        exact.put(key, id);
        byS.computeIfAbsent(subject, k -> new ArrayList<>()).add(id);
        byP.computeIfAbsent(predicate, k -> new ArrayList<>()).add(id);
        byO.computeIfAbsent(obj, k -> new ArrayList<>()).add(id);
        bySP.computeIfAbsent(subject + SEP + predicate, k -> new ArrayList<>()).add(id);
        byPO.computeIfAbsent(predicate + SEP + obj, k -> new ArrayList<>()).add(id);
        bySO.computeIfAbsent(subject + SEP + obj, k -> new ArrayList<>()).add(id);
        return id;
    }

    private Span spanAt(int id, long when) {
        List<Span> history = spans.get(id);
        for (int at = history.size() - 1; at >= 0; at--) {
            Span span = history.get(at);
            if (span.start <= when) {
                return when < span.end ? span : null;
            }
        }
        return null;
    }

    private boolean present(int id, long when) {
        return spanAt(id, when) != null;
    }

    private static String term(String token) {
        return token.equals("?") ? null : token;
    }

    /** The numbers of the triples that can match, from the narrowest index that applies; null means all. */
    private List<Integer> candidates(String s, String p, String o) {
        List<Integer> none = List.of();
        if (s != null && p != null && o != null) {
            Integer id = exact.get(String.join(SEP, s, p, o));
            return id == null ? none : List.of(id);
        }
        if (s != null && p != null) {
            return bySP.getOrDefault(s + SEP + p, none);
        }
        if (p != null && o != null) {
            return byPO.getOrDefault(p + SEP + o, none);
        }
        if (s != null && o != null) {
            return bySO.getOrDefault(s + SEP + o, none);
        }
        if (s != null) {
            return byS.getOrDefault(s, none);
        }
        if (p != null) {
            return byP.getOrDefault(p, none);
        }
        if (o != null) {
            return byO.getOrDefault(o, none);
        }
        return null;
    }

    private int count(List<Integer> candidates) {
        return candidates == null ? triples.size() : candidates.size();
    }

    private List<Integer> each(List<Integer> candidates) {
        if (candidates != null) {
            return candidates;
        }
        List<Integer> all = new ArrayList<>();
        for (int id = 0; id < triples.size(); id++) {
            all.add(id);
        }
        return all;
    }

    // Queries
    private List<List<List<String>>> rows(
            List<List<String>> patterns, List<String> columns, long when, boolean track) {
        List<Found> found = new ArrayList<>();
        search(patterns, new HashMap<>(), new ArrayList<>(), columns, when, track, found);
        Map<String, List<String>> distinct = new HashMap<>();
        for (Found one : found) {
            distinct.put(String.join(SEP, one.row), one.row);
        }
        List<List<String>> rows = new ArrayList<>(distinct.values());
        rows.sort(TripleStore::compareRows);
        List<List<String>> sources = new ArrayList<>();
        if (track) {
            Map<String, Set<String>> byRow = new HashMap<>();
            for (List<String> row : rows) {
                byRow.put(String.join(SEP, row), new TreeSet<>());
            }
            for (Found one : found) {
                Set<String> names = byRow.get(String.join(SEP, one.row));
                for (int id : one.used) {
                    Span span = spanAt(id, when);
                    if (span == null) {
                        continue;
                    }
                    for (int at = 0; at < span.names.size(); at++) {
                        if (span.times.get(at) <= when) {
                            names.add(span.names.get(at));
                        }
                    }
                }
            }
            for (List<String> row : rows) {
                sources.add(new ArrayList<>(byRow.get(String.join(SEP, row))));
            }
        }
        return List.of(rows, sources);
    }

    private void search(
            List<List<String>> remaining,
            Map<String, String> bindings,
            List<Integer> used,
            List<String> columns,
            long when,
            boolean track,
            List<Found> found) {
        if (remaining.isEmpty()) {
            List<String> row = new ArrayList<>();
            for (String name : columns) {
                row.add(bindings.get(name));
            }
            int[] ids = new int[track ? used.size() : 0];
            for (int at = 0; at < ids.length; at++) {
                ids[at] = used.get(at);
            }
            found.add(new Found(row, ids));
            return;
        }
        int best = 0;
        long bestCost = Long.MAX_VALUE;
        for (int at = 0; at < remaining.size(); at++) {
            long cost = cost(remaining.get(at), bindings);
            if (cost < bestCost) {
                bestCost = cost;
                best = at;
            }
        }
        List<String> pattern = remaining.get(best);
        List<List<String>> rest = new ArrayList<>(remaining);
        rest.remove(best);
        for (Match one : matches(pattern, bindings, when)) {
            List<String> undo = new ArrayList<>();
            if (unify(pattern, one.ends, bindings, undo)) {
                if (one.id >= 0) {
                    used.add(one.id);
                }
                search(rest, bindings, used, columns, when, track, found);
                if (one.id >= 0) {
                    used.remove(used.size() - 1);
                }
            }
            for (String name : undo) {
                bindings.remove(name);
            }
        }
    }

    private static String value(String token, Map<String, String> bindings) {
        if (token.equals("?")) {
            return null;
        }
        if (token.startsWith("?")) {
            return bindings.get(token);
        }
        return token;
    }

    private static boolean unify(
            List<String> pattern, String[] ends, Map<String, String> bindings, List<String> undo) {
        String[] tokens = ends.length == 3
                ? new String[] {pattern.get(0), pattern.get(1), pattern.get(2)}
                : new String[] {pattern.get(0), pattern.get(2)};
        for (int at = 0; at < tokens.length; at++) {
            String token = tokens[at];
            if (token.equals("?")) {
                continue;
            }
            if (!token.startsWith("?")) {
                if (!token.equals(ends[at])) {
                    return false;
                }
            } else if (bindings.containsKey(token)) {
                if (!bindings.get(token).equals(ends[at])) {
                    return false;
                }
            } else {
                bindings.put(token, ends[at]);
                undo.add(token);
            }
        }
        return true;
    }

    private long cost(List<String> pattern, Map<String, String> bindings) {
        String s = value(pattern.get(0), bindings);
        String p = value(pattern.get(1), bindings);
        String o = value(pattern.get(2), bindings);
        if (pattern.get(1).endsWith("+")) {
            if (s == null && o == null) {
                return HUGE;
            }
            String predicate = pattern.get(1);
            return byP.getOrDefault(predicate.substring(0, predicate.length() - 1), List.of()).size();
        }
        return count(candidates(s, p, o));
    }

    private List<Match> matches(List<String> pattern, Map<String, String> bindings, long when) {
        String s = value(pattern.get(0), bindings);
        String p = value(pattern.get(1), bindings);
        String o = value(pattern.get(2), bindings);
        List<Match> found = new ArrayList<>();
        if (pattern.get(1).endsWith("+")) {
            String predicate = pattern.get(1);
            for (String[] pair : pathPairs(s, predicate.substring(0, predicate.length() - 1), o, when)) {
                found.add(new Match(pair, -1));
            }
            return found;
        }
        for (int id : each(candidates(s, p, o))) {
            if (present(id, when)) {
                found.add(new Match(triples.get(id), id));
            }
        }
        return found;
    }

    private List<String[]> pathPairs(String s, String p, String o, long when) {
        List<String[]> pairs = new ArrayList<>();
        if (s != null) {
            Set<String> reached = reach(s, p, true, when);
            if (o != null) {
                if (reached.contains(o)) {
                    pairs.add(new String[] {s, o});
                }
                return pairs;
            }
            for (String node : reached) {
                pairs.add(new String[] {s, node});
            }
            return pairs;
        }
        if (o != null) {
            for (String node : reach(o, p, false, when)) {
                pairs.add(new String[] {node, o});
            }
            return pairs;
        }
        Set<String> starts = new LinkedHashSet<>();
        for (int id : byP.getOrDefault(p, List.of())) {
            if (present(id, when)) {
                starts.add(triples.get(id)[0]);
            }
        }
        for (String start : starts) {
            for (String node : reach(start, p, true, when)) {
                pairs.add(new String[] {start, node});
            }
        }
        return pairs;
    }

    /** The nodes at the end of one or more hops; the start is in it only through a cycle. */
    private Set<String> reach(String start, String p, boolean forward, long when) {
        Set<String> seen = new HashSet<>();
        List<String> queue = new ArrayList<>();
        queue.add(start);
        for (int next = 0; next < queue.size(); next++) {
            String node = queue.get(next);
            List<Integer> ids = forward
                    ? bySP.getOrDefault(node + SEP + p, List.of())
                    : byPO.getOrDefault(p + SEP + node, List.of());
            for (int id : ids) {
                if (!present(id, when)) {
                    continue;
                }
                String following = forward ? triples.get(id)[2] : triples.get(id)[0];
                if (seen.add(following)) {
                    queue.add(following);
                }
            }
        }
        return seen;
    }

    private static int compareRows(List<String> a, List<String> b) {
        for (int at = 0; at < a.size(); at++) {
            int order = a.get(at).compareTo(b.get(at));
            if (order != 0) {
                return order;
            }
        }
        return 0;
    }
}
