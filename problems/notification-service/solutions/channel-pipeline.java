import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class NotificationService {
    private static final List<String> CHANNEL_ORDER = List.of("EMAIL", "SMS", "PUSH");
    private static final int MAX_RETRIES = 3;
    private static final long BASE_RETRY_DELAY = 1000;
    private static final Pattern PLACEHOLDER = Pattern.compile("\\{([^{}]*)\\}");

    private interface Channel {
        String format(String address, String text);
    }

    private static final class EmailChannel implements Channel {
        public String format(String address, String text) {
            return address + ": " + text;
        }
    }

    /** A channel with a length limit: a longer text is cut so that it ends in {@code ...} and fits. */
    private record TruncatingChannel(int limit) implements Channel {
        public String format(String address, String text) {
            String fitted = text.length() > limit ? text.substring(0, limit - 3) + "..." : text;
            return address + ": " + fitted;
        }
    }

    private record Template(String body) {
        String render(List<String> params) {
            Map<String, String> values = new HashMap<>();
            for (String param : params) {
                String[] parts = param.split("=", 2);
                if (parts.length == 2) {
                    values.put(parts[0], parts[1]);
                }
            }
            return PLACEHOLDER.matcher(body)
                    .replaceAll(match -> Matcher.quoteReplacement(values.getOrDefault(match.group(1), "")));
        }
    }

    /** At most {@code limit} accepted notifications per user in any {@code window} milliseconds. */
    private static final class SlidingWindowLimiter {
        private final int limit;
        private final long window;
        private final Map<String, Deque<Long>> accepted = new HashMap<>();

        SlidingWindowLimiter(int limit, long window) {
            this.limit = limit;
            this.window = window;
        }

        boolean tryAcquire(String userId, long now) {
            Deque<Long> times = accepted.computeIfAbsent(userId, user -> new ArrayDeque<>());
            while (!times.isEmpty() && times.peekFirst() <= now - window) {
                times.pollFirst();
            }
            if (times.size() >= limit) {
                return false;
            }
            times.addLast(now);
            return true;
        }
    }

    private static final class ChannelState {
        final Channel channel;
        SlidingWindowLimiter limiter;
        long outageStart;
        long outageEnd; // empty outage while start == end
        int delivered;
        int retries;
        int dropped;
        int rateLimited;

        ChannelState(Channel channel) {
            this.channel = channel;
        }

        boolean isDown(long now) {
            return outageStart <= now && now < outageEnd;
        }

        int[] stats() {
            return new int[] {delivered, retries, dropped, rateLimited};
        }
    }

    private static final class Contact {
        final String address;
        boolean enabled = true;

        Contact(String address) {
            this.address = address;
        }
    }

    private record Attempt(long due, long sequence, String userId, String channel, String payload, int retriesLeft) {
    }

    private record ContactKey(String userId, String channel) {
    }

    private final Map<String, ChannelState> channels = Map.of(
            "EMAIL", new ChannelState(new EmailChannel()),
            "SMS", new ChannelState(new TruncatingChannel(20)),
            "PUSH", new ChannelState(new TruncatingChannel(30)));
    private final Map<ContactKey, Contact> contacts = new HashMap<>();
    private final Map<String, Template> templates = new HashMap<>();
    private final PriorityQueue<Attempt> retries =
            new PriorityQueue<>(Comparator.comparingLong(Attempt::due).thenComparingLong(Attempt::sequence));
    private long sequence;
    private final Map<ContactKey, List<String>> inbox = new HashMap<>();

    public NotificationService() {
    }

    public boolean addContact(String userId, String channel, String address) {
        if (!channels.containsKey(channel)) {
            return false;
        }
        contacts.put(new ContactKey(userId, channel), new Contact(address));
        return true;
    }

    public boolean setPreference(String userId, String channel, boolean enabled) {
        Contact contact = contacts.get(new ContactKey(userId, channel));
        if (contact == null) {
            return false;
        }
        contact.enabled = enabled;
        return true;
    }

    public boolean addTemplate(String templateId, String body) {
        return templates.putIfAbsent(templateId, new Template(body)) == null;
    }

    public boolean setRateLimit(String channel, int limit, long windowMs) {
        ChannelState state = channels.get(channel);
        if (state == null) {
            return false;
        }
        state.limiter = new SlidingWindowLimiter(limit, windowMs);
        return true;
    }

    public boolean setOutage(String channel, long start, long end) {
        ChannelState state = channels.get(channel);
        if (state == null) {
            return false;
        }
        state.outageStart = start;
        state.outageEnd = end;
        return true;
    }

    public int send(long timestamp, String userId, String templateId, List<String> params) {
        processRetries(timestamp);
        Template template = templates.get(templateId);
        if (template == null) {
            return -1;
        }
        String text = template.render(params);
        int accepted = 0;
        for (String name : CHANNEL_ORDER) {
            Contact contact = contacts.get(new ContactKey(userId, name));
            if (contact == null || !contact.enabled) {
                continue;
            }
            ChannelState state = channels.get(name);
            if (state.limiter != null && !state.limiter.tryAcquire(userId, timestamp)) {
                state.rateLimited++;
                continue;
            }
            accepted++;
            String payload = state.channel.format(contact.address, text);
            attempt(newAttempt(timestamp, userId, name, payload, MAX_RETRIES));
        }
        return accepted;
    }

    public List<String> delivered(long timestamp, String userId, String channel) {
        processRetries(timestamp);
        return List.copyOf(inbox.getOrDefault(new ContactKey(userId, channel), List.of()));
    }

    public int[] stats(long timestamp, String channel) {
        processRetries(timestamp);
        ChannelState state = channels.get(channel);
        return state == null ? new int[0] : state.stats();
    }

    private Attempt newAttempt(long due, String userId, String channel, String payload, int retriesLeft) {
        sequence++;
        return new Attempt(due, sequence, userId, channel, payload, retriesLeft);
    }

    /** Deliver now, or schedule the next retry with an exponentially growing delay. */
    private void attempt(Attempt attempt) {
        ChannelState state = channels.get(attempt.channel());
        if (!state.isDown(attempt.due())) {
            state.delivered++;
            inbox.computeIfAbsent(new ContactKey(attempt.userId(), attempt.channel()), key -> new ArrayList<>())
                    .add(attempt.payload());
        } else if (attempt.retriesLeft() == 0) {
            state.dropped++;
        } else {
            int retryNumber = MAX_RETRIES - attempt.retriesLeft() + 1;
            long due = attempt.due() + (BASE_RETRY_DELAY << (retryNumber - 1));
            retries.add(newAttempt(due, attempt.userId(), attempt.channel(), attempt.payload(), attempt.retriesLeft() - 1));
        }
    }

    private void processRetries(long now) {
        while (!retries.isEmpty() && retries.peek().due() <= now) {
            Attempt retry = retries.poll();
            channels.get(retry.channel()).retries++;
            attempt(retry);
        }
    }
}
