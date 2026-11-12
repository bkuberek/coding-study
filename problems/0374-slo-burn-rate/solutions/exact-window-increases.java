import java.util.*;

/**
 * Every counter keeps its samples in time order. The increase over a window walks the samples
 * inside it and adds each step, counting a drop as a restart from zero. A histogram is one such
 * counter per bucket. SLOs, burn rates and alerts are ratios of increases, kept as exact fractions
 * and compared by cross-multiplying.
 */
public class SloMonitor {
    private record Slo(String good, String total, long met, long outOf, long window) {
        long spare() {
            return outOf - met;
        }
    }

    private record Alert(String severity, long longWindow, long shortWindow, long above, long below) {}

    private final Map<String, List<Long>> times = new HashMap<>();
    private final Map<String, List<Long>> values = new HashMap<>();
    private final Map<String, List<Long>> bounds = new HashMap<>();
    private final Map<String, Slo> slos = new HashMap<>();
    private final Map<String, List<Alert>> alerts = new HashMap<>();

    public SloMonitor() {
    }

    // Level 1
    public String scrape(String series, long timestamp, long value) {
        List<Long> seen = times.computeIfAbsent(series, key -> new ArrayList<>());
        if (!seen.isEmpty() && timestamp <= seen.get(seen.size() - 1)) {
            return "out-of-order";
        }
        seen.add(timestamp);
        values.computeIfAbsent(series, key -> new ArrayList<>()).add(value);
        return "ok";
    }

    public int scrapeSeries(String series, long start, long step, List<Long> values) {
        int stored = 0;
        for (int i = 0; i < values.size(); i++) {
            if (scrape(series, start + i * step, values.get(i)).equals("ok")) {
                stored++;
            }
        }
        return stored;
    }

    public long increase(String series, long start, long end) {
        List<Long> got = window(series, start, end, values);
        if (got.size() < 2) {
            return -1;
        }
        long total = 0;
        for (int i = 1; i < got.size(); i++) {
            long before = got.get(i - 1);
            long after = got.get(i);
            total += after >= before ? after - before : after;
        }
        return total;
    }

    public String rate(String series, long start, long end) {
        List<Long> got = window(series, start, end, times);
        if (got.size() < 2) {
            return "";
        }
        return fraction(increase(series, start, end), got.get(got.size() - 1) - got.get(0));
    }

    public int resets(String series, long start, long end) {
        List<Long> got = window(series, start, end, values);
        int drops = 0;
        for (int i = 1; i < got.size(); i++) {
            if (got.get(i) < got.get(i - 1)) {
                drops++;
            }
        }
        return drops;
    }

    // Level 2
    public String scrapeHistogram(String name, long timestamp, List<Long> bounds, List<Long> counts) {
        List<Long> seen = times.getOrDefault(name + ":le=inf", List.of());
        if (!seen.isEmpty() && timestamp <= seen.get(seen.size() - 1)) {
            return "out-of-order";
        }
        this.bounds.put(name, new ArrayList<>(bounds));
        for (int i = 0; i < bounds.size(); i++) {
            scrape(name + ":le=" + bounds.get(i), timestamp, counts.get(i));
        }
        scrape(name + ":le=inf", timestamp, counts.get(bounds.size()));
        return "ok";
    }

    public String fractionWithin(String name, long threshold, long start, long end) {
        long[] counts = buckets(name, start, end);
        if (counts == null) {
            return "";
        }
        int index = bounds.get(name).indexOf(threshold);
        return index < 0 ? "" : fraction(counts[index], counts[counts.length - 1]);
    }

    public String quantile(String name, String q, long start, long end) {
        long[] counts = buckets(name, start, end);
        if (counts == null) {
            return "";
        }
        long[] parsed = parseFraction(q);
        long top = parsed[0];
        long bottom = parsed[1];
        List<Long> limits = bounds.get(name);
        long total = counts[counts.length - 1];
        // The rank is q * total; the first bucket whose count reaches it holds the quantile.
        int index = 0;
        while (counts[index] * bottom < top * total) {
            index++;
        }
        if (index == limits.size()) {
            return Long.toString(limits.get(limits.size() - 1));
        }
        long lower = index > 0 ? limits.get(index - 1) : 0;
        long before = index > 0 ? counts[index - 1] : 0;
        long inside = counts[index] - before;
        long numerator = lower * bottom * inside + (limits.get(index) - lower) * (top * total - bottom * before);
        return fraction(numerator, bottom * inside);
    }

    // Level 3
    public String defineSlo(String name, String goodSeries, String totalSeries, String objective, long window) {
        if (slos.containsKey(name)) {
            return "duplicate";
        }
        long[] parsed = parseFraction(objective);
        if (parsed[0] <= 0 || parsed[0] >= parsed[1]) {
            return "bad-objective";
        }
        slos.put(name, new Slo(goodSeries, totalSeries, parsed[0], parsed[1], window));
        alerts.put(name, new ArrayList<>());
        return "ok";
    }

    public String sli(String name, long at) {
        Slo slo = slos.get(name);
        long[] counts = slo == null ? null : counts(slo, at, slo.window());
        return counts == null ? "" : fraction(counts[1] - counts[0], counts[1]);
    }

    public String budgetRemaining(String name, long at) {
        Slo slo = slos.get(name);
        long[] left = slo == null ? null : left(slo, at);
        return left == null ? "" : fraction(left[0], left[1]);
    }

    public String burnRate(String name, long at, long lookback) {
        Slo slo = slos.get(name);
        long[] counts = slo == null ? null : counts(slo, at, lookback);
        if (counts == null) {
            return "";
        }
        return fraction(counts[0] * slo.outOf(), counts[1] * slo.spare());
    }

    public long timeToExhaustion(String name, long at, long lookback) {
        Slo slo = slos.get(name);
        long[] left = slo == null ? null : left(slo, at);
        if (left == null) {
            return -1;
        }
        if (left[0] <= 0) {
            return 0;
        }
        long[] recent = counts(slo, at, lookback);
        if (recent == null || recent[0] == 0) {
            return -1;
        }
        long[] counts = counts(slo, at, slo.window());
        // remaining * window / burn rate, with every product below 2^63.
        long numerator = slo.window() * (counts[1] * slo.spare() - counts[0] * slo.outOf()) * recent[1];
        return numerator / (counts[1] * recent[0] * slo.outOf());
    }

    // Level 4
    public String addAlert(String slo, String severity, long longWindow, long shortWindow, String threshold) {
        List<Alert> list = alerts.get(slo);
        if (list == null) {
            return "unknown-slo";
        }
        for (Alert alert : list) {
            if (alert.severity().equals(severity)) {
                return "duplicate";
            }
        }
        if (longWindow <= 0 || shortWindow < 0 || shortWindow >= longWindow) {
            return "bad-windows";
        }
        long[] parsed = parseFraction(threshold);
        list.add(new Alert(severity, longWindow, shortWindow, parsed[0], parsed[1]));
        return "ok";
    }

    public List<String> firing(String slo, long at) {
        List<String> found = new ArrayList<>();
        Slo target = slos.get(slo);
        if (target == null) {
            return found;
        }
        for (Alert alert : alerts.get(slo)) {
            if (fires(target, alert, at)) {
                found.add(alert.severity());
            }
        }
        return found;
    }

    public List<String> timeline(String slo, long start, long end, long step) {
        List<String> events = new ArrayList<>();
        Slo target = slos.get(slo);
        if (target == null) {
            return events;
        }
        List<Alert> list = alerts.get(slo);
        boolean[] state = new boolean[list.size()];
        for (long at = start; at <= end; at += step) {
            for (int i = 0; i < list.size(); i++) {
                boolean now = fires(target, list.get(i), at);
                if (now != state[i]) {
                    events.add(at + " " + list.get(i).severity() + " " + (now ? "start" : "stop"));
                    state[i] = now;
                }
            }
        }
        return events;
    }

    // Helpers
    private static long gcd(long a, long b) {
        return b == 0 ? Math.abs(a) : gcd(b, a % b);
    }

    /** {@code p/q} in lowest terms with q > 0, or {@code p} for a whole number. */
    private static String fraction(long numerator, long denominator) {
        if (denominator < 0) {
            numerator = -numerator;
            denominator = -denominator;
        }
        long common = gcd(numerator, denominator);
        numerator /= common;
        denominator /= common;
        return denominator == 1 ? Long.toString(numerator) : numerator + "/" + denominator;
    }

    private static long[] parseFraction(String text) {
        int slash = text.indexOf('/');
        if (slash < 0) {
            return new long[] {Long.parseLong(text), 1};
        }
        return new long[] {Long.parseLong(text.substring(0, slash)), Long.parseLong(text.substring(slash + 1))};
    }

    /** The first index whose time is at least {@code time}. */
    private static int lowerBound(List<Long> sorted, long time) {
        int low = 0;
        int high = sorted.size();
        while (low < high) {
            int mid = (low + high) >>> 1;
            if (sorted.get(mid) < time) {
                low = mid + 1;
            } else {
                high = mid;
            }
        }
        return low;
    }

    /** The part of {@code column} (the times or the values of the series) inside the window. */
    private List<Long> window(String series, long start, long end, Map<String, List<Long>> column) {
        List<Long> seen = times.getOrDefault(series, List.of());
        int low = lowerBound(seen, start);
        int high = lowerBound(seen, end + 1);
        return column.getOrDefault(series, List.of()).subList(low, Math.max(low, high));
    }

    /** The increase of every bucket over the window, or null when the window has no requests. */
    private long[] buckets(String name, long start, long end) {
        List<Long> limits = bounds.get(name);
        if (limits == null) {
            return null;
        }
        long[] counts = new long[limits.size() + 1];
        for (int i = 0; i < limits.size(); i++) {
            counts[i] = increase(name + ":le=" + limits.get(i), start, end);
        }
        counts[limits.size()] = increase(name + ":le=inf", start, end);
        return counts[limits.size()] > 0 ? counts : null;
    }

    /** {bad, total} over [at - span, at], or null without requests. */
    private long[] counts(Slo slo, long at, long span) {
        long total = increase(slo.total(), at - span, at);
        long good = increase(slo.good(), at - span, at);
        if (total <= 0 || good < 0) {
            return null;
        }
        return new long[] {total - good, total};
    }

    /** The share of the budget left, as {numerator, denominator}. */
    private long[] left(Slo slo, long at) {
        long[] counts = counts(slo, at, slo.window());
        if (counts == null) {
            return null;
        }
        return new long[] {counts[1] * slo.spare() - counts[0] * slo.outOf(), counts[1] * slo.spare()};
    }

    private boolean burnsAbove(Slo slo, long at, long span, Alert alert) {
        long[] counts = counts(slo, at, span);
        if (counts == null) {
            return false;
        }
        return counts[0] * slo.outOf() * alert.below() > alert.above() * counts[1] * slo.spare();
    }

    private boolean fires(Slo slo, Alert alert, long at) {
        if (!burnsAbove(slo, at, alert.longWindow(), alert)) {
            return false;
        }
        return alert.shortWindow() == 0 || burnsAbove(slo, at, alert.shortWindow(), alert);
    }
}
