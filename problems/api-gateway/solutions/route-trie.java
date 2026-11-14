import java.util.*;

public class ApiGateway {
    private static final String NOT_FOUND = "404";
    private static final String TOO_MANY_REQUESTS = "429";
    private static final String UNAVAILABLE = "503";

    private enum BreakerState { CLOSED, OPEN, HALF_OPEN }

    private static List<String> segmentsOf(String path) {
        return Arrays.stream(path.split("/")).filter(segment -> !segment.isEmpty()).toList();
    }

    /** One trie level: literal children, one shared parameter child, and the routes ending here. */
    private static final class RouteNode {
        final Map<String, RouteNode> literals = new HashMap<>();
        RouteNode parameter;
        String upstream;
        String wildcard;

        RouteNode child(String segment) {
            if (segment.startsWith(":")) {
                if (parameter == null) {
                    parameter = new RouteNode();
                }
                return parameter;
            }
            return literals.computeIfAbsent(segment, s -> new RouteNode());
        }

        /** The most specific upstream: literal before parameter before wildcard, left to right. */
        String match(List<String> segments, int index) {
            if (index == segments.size()) {
                return upstream;
            }
            RouteNode literal = literals.get(segments.get(index));
            String found = literal == null ? null : literal.match(segments, index + 1);
            if (found == null && parameter != null) {
                found = parameter.match(segments, index + 1);
            }
            return found != null ? found : wildcard;
        }
    }

    private static final class RouteTable {
        private final Map<String, RouteNode> roots = new HashMap<>();

        boolean add(String method, String pattern, String upstream) {
            List<String> segments = segmentsOf(pattern);
            RouteNode node = end(method, segments);
            if (endsWithWildcard(segments)) {
                if (node.wildcard != null) {
                    return false;
                }
                node.wildcard = upstream;
            } else {
                if (node.upstream != null) {
                    return false;
                }
                node.upstream = upstream;
            }
            return true;
        }

        boolean remove(String method, String pattern) {
            List<String> segments = segmentsOf(pattern);
            RouteNode node = end(method, segments);
            String found;
            if (endsWithWildcard(segments)) {
                found = node.wildcard;
                node.wildcard = null;
            } else {
                found = node.upstream;
                node.upstream = null;
            }
            return found != null;
        }

        String match(String method, String path) {
            RouteNode root = roots.get(method);
            return root == null ? null : root.match(segmentsOf(path), 0);
        }

        private static boolean endsWithWildcard(List<String> segments) {
            return !segments.isEmpty() && segments.get(segments.size() - 1).equals("*");
        }

        /** The node where the pattern ends, before its wildcard if it has one. */
        private RouteNode end(String method, List<String> segments) {
            RouteNode node = roots.computeIfAbsent(method, m -> new RouteNode());
            int length = endsWithWildcard(segments) ? segments.size() - 1 : segments.size();
            for (String segment : segments.subList(0, length)) {
                node = node.child(segment);
            }
            return node;
        }
    }

    private interface RateLimiter {
        boolean allows(long now);

        void record(long now);
    }

    private static final class FixedWindow implements RateLimiter {
        private final int limit;
        private final long window;
        private long current = -1;
        private int used;

        FixedWindow(int limit, long window) {
            this.limit = limit;
            this.window = window;
        }

        public boolean allows(long now) {
            return now / window != current || used < limit;
        }

        public void record(long now) {
            if (now / window != current) {
                current = now / window;
                used = 0;
            }
            used++;
        }
    }

    private static final class SlidingWindow implements RateLimiter {
        private final int limit;
        private final long window;
        private final Deque<Long> accepted = new ArrayDeque<>();

        SlidingWindow(int limit, long window) {
            this.limit = limit;
            this.window = window;
        }

        public boolean allows(long now) {
            while (!accepted.isEmpty() && accepted.peekFirst() <= now - window) {
                accepted.pollFirst();
            }
            return accepted.size() < limit;
        }

        public void record(long now) {
            accepted.addLast(now);
        }
    }

    private static final class Client {
        RateLimiter limiter;
        Long quota;

        boolean allows(long now) {
            boolean withinRate = limiter == null || limiter.allows(now);
            return withinRate && (quota == null || quota > 0);
        }

        void record(long now) {
            if (limiter != null) {
                limiter.record(now);
            }
            if (quota != null) {
                quota--;
            }
        }
    }

    private static final class CircuitBreaker {
        private final int threshold;
        private final long cooldown;
        private int failures;
        private Long openedAt;
        private boolean trialInFlight;

        CircuitBreaker(int threshold, long cooldown) {
            this.threshold = threshold;
            this.cooldown = cooldown;
        }

        BreakerState state(long now) {
            if (openedAt == null) {
                return BreakerState.CLOSED;
            }
            return now >= openedAt + cooldown ? BreakerState.HALF_OPEN : BreakerState.OPEN;
        }

        boolean allows(long now) {
            BreakerState state = state(now);
            return state == BreakerState.CLOSED || (state == BreakerState.HALF_OPEN && !trialInFlight);
        }

        void onDispatch(long now) {
            if (state(now) == BreakerState.HALF_OPEN) {
                trialInFlight = true;
            }
        }

        BreakerState record(long now, boolean success) {
            switch (state(now)) {
                case HALF_OPEN -> {
                    trialInFlight = false;
                    openedAt = success ? null : now;
                }
                case CLOSED -> {
                    failures = success ? 0 : failures + 1;
                    if (failures >= threshold) {
                        failures = 0;
                        openedAt = now;
                    }
                }
                case OPEN -> {
                    // Results that arrive while the circuit is open are stale.
                }
            }
            return state(now);
        }
    }

    private final RouteTable routes = new RouteTable();
    private final Map<String, Client> clients = new HashMap<>();
    private final Map<String, CircuitBreaker> breakers = new HashMap<>();

    public ApiGateway() {
    }

    // Level 1
    public boolean addRoute(long timestamp, String method, String pattern, String upstream) {
        return routes.add(method, pattern, upstream);
    }

    public boolean removeRoute(long timestamp, String method, String pattern) {
        return routes.remove(method, pattern);
    }

    public String route(long timestamp, String clientId, String method, String path) {
        String upstream = routes.match(method, path);
        if (upstream == null) {
            return NOT_FOUND;
        }
        CircuitBreaker breaker = breakers.get(upstream);
        if (breaker != null && !breaker.allows(timestamp)) {
            return UNAVAILABLE;
        }
        Client client = clients.get(clientId);
        if (client != null && !client.allows(timestamp)) {
            return TOO_MANY_REQUESTS;
        }
        if (client != null) {
            client.record(timestamp);
        }
        if (breaker != null) {
            breaker.onDispatch(timestamp);
        }
        return upstream;
    }

    // Level 2
    public void setClientLimit(long timestamp, String clientId, int limit, long windowMs) {
        client(clientId).limiter = new FixedWindow(limit, windowMs);
    }

    // Level 3
    public void setClientSlidingLimit(long timestamp, String clientId, int limit, long windowMs) {
        client(clientId).limiter = new SlidingWindow(limit, windowMs);
    }

    public void setClientQuota(long timestamp, String clientId, long quota) {
        client(clientId).quota = quota;
    }

    public long remainingQuota(long timestamp, String clientId) {
        Client client = clients.get(clientId);
        return client == null || client.quota == null ? -1 : client.quota;
    }

    // Level 4
    public void setBreaker(long timestamp, String upstream, int failureThreshold, long cooldownMs) {
        breakers.put(upstream, new CircuitBreaker(failureThreshold, cooldownMs));
    }

    public String reportResult(long timestamp, String upstream, boolean success) {
        CircuitBreaker breaker = breakers.get(upstream);
        return breaker == null ? "" : breaker.record(timestamp, success).name();
    }

    public String breakerState(long timestamp, String upstream) {
        CircuitBreaker breaker = breakers.get(upstream);
        return breaker == null ? "" : breaker.state(timestamp).name();
    }

    private Client client(String clientId) {
        return clients.computeIfAbsent(clientId, id -> new Client());
    }
}
