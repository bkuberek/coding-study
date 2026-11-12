import java.util.*;

/**
 * Every double keeps its stub rules per method, newest last, and a mock also keeps its
 * expectations in the order they were set. One log holds every call in the order it was made,
 * with its time, and each double keeps the positions of its own calls in that log, so the spy
 * questions read short lists. Timers wait in a priority queue ordered by due time, then by the
 * sequence number they got when they were last put in, so equal times fire in scheduling order.
 */
public class Doubles {
    private static final String UNKNOWN = "!unknown";
    private static final String UNEXPECTED = "!unexpected";

    private static boolean fits(List<String> pattern, List<String> args) {
        if (pattern.size() != args.size()) {
            return false;
        }
        for (int i = 0; i < pattern.size(); i++) {
            String p = pattern.get(i);
            if (!p.equals("*") && !p.equals(args.get(i))) {
                return false;
            }
        }
        return true;
    }

    private static final class Rule {
        final List<String> pattern;
        final List<String> answers;
        int used;

        Rule(List<String> pattern, List<String> answers) {
            this.pattern = pattern;
            this.answers = answers;
        }

        String nextAnswer() {
            String answer = answers.get(Math.min(used, answers.size() - 1));
            used++;
            return answer;
        }
    }

    private static final class Expectation {
        final String method;
        final List<String> pattern;
        final String answer;
        final int times;
        int used;

        Expectation(String method, List<String> pattern, String answer, int times) {
            this.method = method;
            this.pattern = pattern;
            this.answer = answer;
            this.times = times;
        }
    }

    private record Unexpected(String method, List<String> args) {
    }

    private static final class DoubleState {
        final boolean mock;
        final boolean strict;
        final Map<String, List<Rule>> rules = new HashMap<>();
        final Map<String, String> fallback = new HashMap<>();
        final List<Expectation> expectations = new ArrayList<>();
        final List<Unexpected> unexpected = new ArrayList<>();
        final List<Integer> calls = new ArrayList<>();

        DoubleState(boolean mock, boolean strict) {
            this.mock = mock;
            this.strict = strict;
        }

        String answer(String method, List<String> args) {
            for (Expectation e : expectations) {
                if (e.method.equals(method) && e.used < e.times && fits(e.pattern, args)) {
                    e.used++;
                    return e.answer;
                }
            }
            List<Rule> methodRules = rules.getOrDefault(method, List.of());
            for (int i = methodRules.size() - 1; i >= 0; i--) {
                if (fits(methodRules.get(i).pattern, args)) {
                    return methodRules.get(i).nextAnswer();
                }
            }
            String answer = fallback.get(method);
            if (answer != null) {
                return answer;
            }
            if (!mock) {
                return "";
            }
            unexpected.add(new Unexpected(method, args));
            return strict ? UNEXPECTED : "";
        }
    }

    private record LoggedCall(String name, String method, List<String> args, long time) {
    }

    private static final class Timer {
        final String name;
        final String method;
        final List<String> args;
        final long interval;
        boolean stopped;

        Timer(String name, String method, List<String> args, long interval) {
            this.name = name;
            this.method = method;
            this.args = args;
            this.interval = interval;
        }
    }

    private record Entry(long due, long sequence, int timerId) {
    }

    private static final Comparator<Entry> FIRING_ORDER =
            Comparator.comparingLong(Entry::due).thenComparingLong(Entry::sequence);

    private final Map<String, DoubleState> doubles = new LinkedHashMap<>();
    private final List<LoggedCall> log = new ArrayList<>();
    private final PriorityQueue<Entry> heap = new PriorityQueue<>(FIRING_ORDER);
    private final List<Timer> timers = new ArrayList<>();
    private long clock;
    private long sequence;

    public Doubles() {
    }

    // Level 1
    public boolean addStub(String name) {
        return add(name, false, false);
    }

    public boolean onCall(String name, String method, List<String> args, List<String> answers) {
        DoubleState d = doubles.get(name);
        if (d == null) {
            return false;
        }
        d.rules.computeIfAbsent(method, key -> new ArrayList<>())
                .add(new Rule(List.copyOf(args), List.copyOf(answers)));
        return true;
    }

    public boolean otherwise(String name, String method, String answer) {
        DoubleState d = doubles.get(name);
        if (d == null) {
            return false;
        }
        d.fallback.put(method, answer);
        return true;
    }

    public String call(String name, String method, List<String> args) {
        DoubleState d = doubles.get(name);
        if (d == null) {
            return UNKNOWN;
        }
        List<String> copy = List.copyOf(args);
        d.calls.add(log.size());
        log.add(new LoggedCall(name, method, copy, clock));
        return d.answer(method, copy);
    }

    // Level 2
    public int callCount(String name, String method) {
        return count(name, method, null);
    }

    public int matchCount(String name, String method, List<String> args) {
        return count(name, method, args);
    }

    public List<String> nthCall(String name, int n) {
        DoubleState d = doubles.get(name);
        if (d == null || n == 0 || Math.abs(n) > d.calls.size()) {
            return new ArrayList<>();
        }
        LoggedCall call = log.get(d.calls.get(n > 0 ? n - 1 : d.calls.size() + n));
        List<String> result = new ArrayList<>();
        result.add(call.method());
        result.addAll(call.args());
        return result;
    }

    public boolean inOrder(List<List<String>> steps) {
        int step = 0;
        for (LoggedCall call : log) {
            if (step == steps.size()) {
                break;
            }
            List<String> wanted = steps.get(step);
            if (wanted.get(0).equals(call.name()) && wanted.get(1).equals(call.method())
                    && fits(wanted.subList(2, wanted.size()), call.args())) {
                step++;
            }
        }
        return step == steps.size();
    }

    // Level 3
    public boolean addMock(String name, boolean strict) {
        return add(name, true, strict);
    }

    public boolean expect(String name, String method, List<String> args, String answer, int times) {
        DoubleState d = doubles.get(name);
        if (d == null || !d.mock) {
            return false;
        }
        d.expectations.add(new Expectation(method, List.copyOf(args), answer, times));
        return true;
    }

    public List<String> verify(String name) {
        DoubleState d = doubles.get(name);
        List<String> report = new ArrayList<>();
        if (d == null) {
            report.add(UNKNOWN);
            return report;
        }
        for (Expectation e : d.expectations) {
            if (e.used < e.times) {
                report.add("missing " + name + "." + e.method + "(" + String.join(",", e.pattern) + ") "
                        + e.used + "/" + e.times);
            }
        }
        for (Unexpected u : d.unexpected) {
            report.add("unexpected " + name + "." + u.method() + "(" + String.join(",", u.args()) + ")");
        }
        return report;
    }

    public List<String> verifyAll() {
        List<String> report = new ArrayList<>();
        for (Map.Entry<String, DoubleState> entry : doubles.entrySet()) {
            if (entry.getValue().mock) {
                report.addAll(verify(entry.getKey()));
            }
        }
        return report;
    }

    // Level 4
    public long now() {
        return clock;
    }

    public int schedule(long delay, String name, String method, List<String> args) {
        return timer(delay, 0, name, method, args);
    }

    public int every(long interval, String name, String method, List<String> args) {
        return timer(interval, interval, name, method, args);
    }

    public boolean cancel(int timerId) {
        if (timerId < 1 || timerId > timers.size()) {
            return false;
        }
        Timer timer = timers.get(timerId - 1);
        if (timer.stopped) {
            return false;
        }
        timer.stopped = true;
        return true;
    }

    public List<String> advance(long ms) {
        long end = clock + ms;
        List<String> fired = new ArrayList<>();
        while (!heap.isEmpty() && heap.peek().due() <= end) {
            Entry entry = heap.poll();
            Timer timer = timers.get(entry.timerId() - 1);
            if (timer.stopped) {
                continue;
            }
            clock = entry.due();
            if (timer.interval > 0) {
                push(entry.due() + timer.interval, entry.timerId());
            } else {
                timer.stopped = true;
            }
            fired.add(entry.timerId() + "@" + entry.due());
            call(timer.name, timer.method, timer.args);
        }
        clock = end;
        return fired;
    }

    public List<String> pending() {
        List<Entry> live = new ArrayList<>();
        for (Entry entry : heap) {
            if (!timers.get(entry.timerId() - 1).stopped) {
                live.add(entry);
            }
        }
        live.sort(FIRING_ORDER);
        List<String> result = new ArrayList<>();
        for (Entry entry : live) {
            result.add(entry.timerId() + "@" + entry.due());
        }
        return result;
    }

    public List<Long> callTimes(String name, String method) {
        DoubleState d = doubles.get(name);
        List<Long> times = new ArrayList<>();
        if (d == null) {
            return times;
        }
        for (int position : d.calls) {
            LoggedCall call = log.get(position);
            if (call.method().equals(method)) {
                times.add(call.time());
            }
        }
        return times;
    }

    private int count(String name, String method, List<String> pattern) {
        DoubleState d = doubles.get(name);
        if (d == null) {
            return -1;
        }
        int total = 0;
        for (int position : d.calls) {
            LoggedCall call = log.get(position);
            if (call.method().equals(method) && (pattern == null || fits(pattern, call.args()))) {
                total++;
            }
        }
        return total;
    }

    private boolean add(String name, boolean mock, boolean strict) {
        if (doubles.containsKey(name)) {
            return false;
        }
        doubles.put(name, new DoubleState(mock, strict));
        return true;
    }

    private int timer(long delay, long interval, String name, String method, List<String> args) {
        if (!doubles.containsKey(name)) {
            return -1;
        }
        timers.add(new Timer(name, method, List.copyOf(args), interval));
        push(clock + delay, timers.size());
        return timers.size();
    }

    private void push(long due, int timerId) {
        sequence++;
        heap.add(new Entry(due, sequence, timerId));
    }
}
