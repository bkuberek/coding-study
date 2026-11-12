import java.util.*;

/**
 * Rules are data: each one is a check name, its columns and its parameters, kept in the order they
 * were added. Validation runs every rule over the rows and reports what failed; the gate runs the
 * row rules first, sets aside the rows that quarantine rules reject, and runs the batch rules on
 * what is left.
 */
public class QualityGate {
    private static final Set<String> ROW_CHECKS =
            Set.of("not-null", "type", "allowed", "range", "unique", "references");
    private static final Set<String> BATCH_CHECKS = Set.of("row-count", "drift", "freshness");
    private static final Set<String> ACTIONS = Set.of("warn", "quarantine", "block");
    private static final double EMPTY_SHARE = 0.0001;
    private static final int[] DAYS_IN_MONTH = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};

    private static final class Rule {
        final String ruleId;
        final String check;
        final List<String> columns;
        final List<String> params;
        String action = "block";

        Rule(String ruleId, String check, List<String> columns, List<String> params) {
            this.ruleId = ruleId;
            this.check = check;
            this.columns = columns;
            this.params = params;
        }
    }

    private final Map<String, Integer> index = new HashMap<>();
    private final List<Rule> rules = new ArrayList<>();
    private final Map<String, Rule> byId = new HashMap<>();
    private final Map<String, Set<String>> dimensions = new HashMap<>();
    private List<List<String>> previous = null;
    private long now = 0;
    private List<Integer> aside = new ArrayList<>();

    public QualityGate(List<String> columns) {
        for (int at = 0; at < columns.size(); at++) {
            index.put(columns.get(at), at);
        }
    }

    // Level 1
    public boolean addRule(String ruleId, String check, List<String> columns, List<String> params) {
        boolean known = ROW_CHECKS.contains(check) || BATCH_CHECKS.contains(check);
        if (byId.containsKey(ruleId) || !known || !index.keySet().containsAll(columns)) {
            return false;
        }
        if (check.equals("references") && !dimensions.containsKey(params.get(0))) {
            return false;
        }
        Rule rule = new Rule(ruleId, check, new ArrayList<>(columns), new ArrayList<>(params));
        rules.add(rule);
        byId.put(ruleId, rule);
        return true;
    }

    public List<List<String>> validate(List<List<String>> rows) {
        List<List<String>> report = new ArrayList<>();
        for (Rule rule : rules) {
            report.addAll(findings(rule, rows));
        }
        return report;
    }

    public List<Integer> failingRows(List<List<String>> rows, String ruleId) {
        Rule rule = byId.get(ruleId);
        if (rule == null || BATCH_CHECKS.contains(rule.check)) {
            return new ArrayList<>();
        }
        TreeSet<Integer> failing = new TreeSet<>();
        for (List<Integer> bad : rowFailures(rule, rows).values()) {
            failing.addAll(bad);
        }
        return new ArrayList<>(failing);
    }

    // Level 2
    public int loadDimension(String name, List<String> keys) {
        dimensions.put(name, new HashSet<>(keys));
        return dimensions.get(name).size();
    }

    public int setPreviousBatch(List<List<String>> rows) {
        previous = new ArrayList<>(rows);
        return rows.size();
    }

    // Level 3
    public void setTime(long now) {
        this.now = now;
    }

    // Level 4
    public boolean setAction(String ruleId, String action) {
        Rule rule = byId.get(ruleId);
        if (rule == null || !ACTIONS.contains(action)) {
            return false;
        }
        if (action.equals("quarantine") && BATCH_CHECKS.contains(rule.check)) {
            return false;
        }
        rule.action = action;
        return true;
    }

    public List<List<String>> decide(List<List<String>> rows) {
        TreeSet<Integer> setAside = new TreeSet<>();
        for (Rule rule : rules) {
            if (ROW_CHECKS.contains(rule.check) && rule.action.equals("quarantine")) {
                setAside.addAll(failingRows(rows, rule.ruleId));
            }
        }
        List<List<String>> kept = new ArrayList<>();
        for (int at = 0; at < rows.size(); at++) {
            if (!setAside.contains(at)) {
                kept.add(rows.get(at));
            }
        }
        List<List<String>> findings = new ArrayList<>();
        boolean blocked = false;
        for (Rule rule : rules) {
            List<List<String>> seen = ROW_CHECKS.contains(rule.check) ? rows : kept;
            for (List<String> entry : findings(rule, seen)) {
                List<String> withAction = new ArrayList<>(entry);
                withAction.add(rule.action);
                findings.add(withAction);
                blocked |= rule.action.equals("block");
            }
        }
        List<List<String>> answer = new ArrayList<>();
        if (blocked) {
            aside = new ArrayList<>();
            answer.add(List.of("block", "0", "0"));
        } else {
            aside = new ArrayList<>(setAside);
            previous = kept;
            answer.add(List.of("publish", String.valueOf(kept.size()), String.valueOf(setAside.size())));
        }
        answer.addAll(findings);
        return answer;
    }

    public List<Integer> quarantined() {
        return new ArrayList<>(aside);
    }

    // Helpers
    private List<List<String>> findings(Rule rule, List<List<String>> rows) {
        List<List<String>> found = new ArrayList<>();
        if (ROW_CHECKS.contains(rule.check)) {
            for (Map.Entry<String, List<Integer>> entry : rowFailures(rule, rows).entrySet()) {
                if (!entry.getValue().isEmpty()) {
                    found.add(List.of(rule.ruleId, entry.getKey(), String.valueOf(entry.getValue().size())));
                }
            }
            return found;
        }
        String observed = batchFailure(rule, rows);
        if (observed != null) {
            found.add(List.of(rule.ruleId, String.join("", rule.columns), observed));
        }
        return found;
    }

    /** For each column of a row rule (one joined key for unique), the rows that fail it, in order. */
    private LinkedHashMap<String, List<Integer>> rowFailures(Rule rule, List<List<String>> rows) {
        LinkedHashMap<String, List<Integer>> failures = new LinkedHashMap<>();
        if (rule.check.equals("unique")) {
            Map<String, List<Integer>> groups = new HashMap<>();
            for (int at = 0; at < rows.size(); at++) {
                StringBuilder key = new StringBuilder();
                boolean hasNull = false;
                for (String column : rule.columns) {
                    String part = rows.get(at).get(index.get(column));
                    hasNull |= part.isEmpty();
                    key.append(part.length()).append(':').append(part);
                }
                if (!hasNull) {
                    groups.computeIfAbsent(key.toString(), k -> new ArrayList<>()).add(at);
                }
            }
            List<Integer> bad = new ArrayList<>();
            for (List<Integer> group : groups.values()) {
                if (group.size() > 1) {
                    bad.addAll(group);
                }
            }
            Collections.sort(bad);
            failures.put(String.join("+", rule.columns), bad);
            return failures;
        }
        for (String column : rule.columns) {
            int at = index.get(column);
            List<Integer> bad = new ArrayList<>();
            for (int number = 0; number < rows.size(); number++) {
                if (fails(rule, rows.get(number).get(at))) {
                    bad.add(number);
                }
            }
            failures.put(column, bad);
        }
        return failures;
    }

    private boolean fails(Rule rule, String value) {
        if (rule.check.equals("not-null")) {
            return value.isEmpty();
        }
        if (value.isEmpty()) {
            return false;
        }
        switch (rule.check) {
            case "type":
                return !(rule.params.get(0).equals("int") ? isInt(value) : isDate(value));
            case "allowed":
                return !rule.params.contains(value);
            case "range": {
                if (!isInt(value)) {
                    return false;
                }
                long number = Long.parseLong(value);
                return number < Long.parseLong(rule.params.get(0)) || number > Long.parseLong(rule.params.get(1));
            }
            default:
                return !dimensions.get(rule.params.get(0)).contains(value);
        }
    }

    /** The observed value of a failing batch rule, or null when it passes. */
    private String batchFailure(Rule rule, List<List<String>> rows) {
        if (rule.check.equals("row-count")) {
            if (previous == null) {
                return null;
            }
            long before = previous.size();
            long tolerance = Long.parseLong(rule.params.get(0));
            long low = before * (100 - tolerance) / 100;
            long high = (before * (100 + tolerance) + 99) / 100;
            return rows.size() >= low && rows.size() <= high ? null : String.valueOf(rows.size());
        }
        int column = index.get(rule.columns.get(0));
        List<Long> values = integers(rows, column);
        if (rule.check.equals("freshness")) {
            if (values.isEmpty()) {
                return "none";
            }
            long lag = now - Collections.max(values);
            return lag > Long.parseLong(rule.params.get(0)) ? String.valueOf(lag) : null;
        }
        if (previous == null) {
            return null;
        }
        List<Long> baseline = integers(previous, column);
        if (values.isEmpty() || baseline.isEmpty()) {
            return null;
        }
        long[] edges = new long[rule.params.size() - 1];
        for (int at = 1; at < rule.params.size(); at++) {
            edges[at - 1] = Long.parseLong(rule.params.get(at));
        }
        long units = (long) Math.floor(psi(values, baseline, edges) * 10000 + 0.5);
        if (units < tenThousandths(rule.params.get(0))) {
            return null;
        }
        return (units / 10000) + "." + String.format(Locale.ROOT, "%04d", units % 10000);
    }

    private static List<Long> integers(List<List<String>> rows, int column) {
        List<Long> values = new ArrayList<>();
        for (List<String> row : rows) {
            if (isInt(row.get(column))) {
                values.add(Long.parseLong(row.get(column)));
            }
        }
        return values;
    }

    private static double psi(List<Long> values, List<Long> baseline, long[] edges) {
        double[] actual = shares(values, edges);
        double[] expected = shares(baseline, edges);
        double total = 0;
        for (int bin = 0; bin < actual.length; bin++) {
            total += (actual[bin] - expected[bin]) * Math.log(actual[bin] / expected[bin]);
        }
        return total;
    }

    private static double[] shares(List<Long> sample, long[] edges) {
        int[] counts = new int[edges.length + 1];
        for (long value : sample) {
            counts[binOf(value, edges)]++;
        }
        double[] shares = new double[counts.length];
        for (int bin = 0; bin < counts.length; bin++) {
            shares[bin] = counts[bin] == 0 ? EMPTY_SHARE : (double) counts[bin] / sample.size();
        }
        return shares;
    }

    /** The number of edges at or below the value. */
    private static int binOf(long value, long[] edges) {
        int low = 0;
        int high = edges.length;
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (edges[middle] <= value) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return low;
    }

    private static boolean allDigits(String text) {
        for (int at = 0; at < text.length(); at++) {
            char ch = text.charAt(at);
            if (ch < '0' || ch > '9') {
                return false;
            }
        }
        return true;
    }

    private static boolean isInt(String text) {
        String digits = text.startsWith("-") ? text.substring(1) : text;
        return digits.length() >= 1 && digits.length() <= 15 && allDigits(digits);
    }

    private static boolean isDate(String text) {
        if (text.length() != 10 || text.charAt(4) != '-' || text.charAt(7) != '-') {
            return false;
        }
        String yearText = text.substring(0, 4);
        String monthText = text.substring(5, 7);
        String dayText = text.substring(8, 10);
        if (!allDigits(yearText) || !allDigits(monthText) || !allDigits(dayText)) {
            return false;
        }
        int year = Integer.parseInt(yearText);
        int month = Integer.parseInt(monthText);
        int day = Integer.parseInt(dayText);
        if (year < 1 || month < 1 || month > 12) {
            return false;
        }
        boolean leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
        int last = month == 2 && leap ? 29 : DAYS_IN_MONTH[month - 1];
        return day >= 1 && day <= last;
    }

    /** A non-negative decimal with at most four places, in units of 0.0001. */
    private static long tenThousandths(String decimal) {
        int dot = decimal.indexOf('.');
        String whole = dot < 0 ? decimal : decimal.substring(0, dot);
        String fraction = dot < 0 ? "" : decimal.substring(dot + 1);
        return Long.parseLong(whole) * 10000 + Long.parseLong((fraction + "0000").substring(0, 4));
    }
}
