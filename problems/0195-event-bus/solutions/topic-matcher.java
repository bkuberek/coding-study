import java.util.*;

public class EventBus {
    private static final String NO_SUBSCRIBER = "-";

    /** Dot-separated segments; {@code *} matches exactly one segment and {@code #} zero or more. */
    private static final class TopicPattern {
        private final String[] segments;

        TopicPattern(String text) {
            segments = text.split("\\.");
        }

        boolean matches(String topic) {
            String[] words = topic.split("\\.");
            // matched[p][w]: segments from p match words from w.
            boolean[][] matched = new boolean[segments.length + 1][words.length + 1];
            matched[segments.length][words.length] = true;
            for (int p = segments.length - 1; p >= 0; p--) {
                for (int w = words.length; w >= 0; w--) {
                    if (segments[p].equals("#")) {
                        matched[p][w] = matched[p + 1][w] || (w < words.length && matched[p][w + 1]);
                    } else {
                        boolean same = w < words.length && (segments[p].equals("*") || segments[p].equals(words[w]));
                        matched[p][w] = same && matched[p + 1][w + 1];
                    }
                }
            }
            return matched[0][0];
        }
    }

    private record Event(String topic, String payload) {
        String render() {
            return topic + ":" + payload;
        }
    }

    private static final class Subscriber {
        final String id;
        final Map<String, TopicPattern> patterns = new LinkedHashMap<>();
        final Deque<Event> inbox = new ArrayDeque<>();
        Integer limit; // null: unbounded

        Subscriber(String id) {
            this.id = id;
        }

        boolean wants(String topic) {
            return patterns.values().stream().anyMatch(pattern -> pattern.matches(topic));
        }

        /** Accept the event unless the inbox is full. */
        boolean offer(Event event) {
            if (limit != null && inbox.size() >= limit) {
                return false;
            }
            inbox.addLast(event);
            return true;
        }

        List<String> take(int count) {
            List<String> taken = new ArrayList<>();
            while (!inbox.isEmpty() && taken.size() < count) {
                taken.add(inbox.pollFirst().render());
            }
            return taken;
        }
    }

    private static final class DeadLetterQueue {
        private final Deque<String> letters = new ArrayDeque<>();

        void add(String subscriberId, Event event) {
            letters.addLast(subscriberId + ":" + event.render());
        }

        List<String> drain(int count) {
            List<String> drained = new ArrayList<>();
            while (!letters.isEmpty() && drained.size() < count) {
                drained.add(letters.pollFirst());
            }
            return drained;
        }
    }

    private final Map<String, Subscriber> subscribers = new HashMap<>();
    private final DeadLetterQueue deadLetterQueue = new DeadLetterQueue();

    public EventBus() {
    }

    public boolean subscribe(String subscriberId, String pattern) {
        Subscriber subscriber = subscribers.computeIfAbsent(subscriberId, Subscriber::new);
        if (subscriber.patterns.containsKey(pattern)) {
            return false;
        }
        subscriber.patterns.put(pattern, new TopicPattern(pattern));
        return true;
    }

    public boolean unsubscribe(String subscriberId, String pattern) {
        Subscriber subscriber = subscribers.get(subscriberId);
        return subscriber != null && subscriber.patterns.remove(pattern) != null;
    }

    public int publish(String topic, String payload) {
        Event event = new Event(topic, payload);
        List<Subscriber> interested = subscribers.values().stream()
                .filter(subscriber -> subscriber.wants(topic))
                .sorted(Comparator.comparing(subscriber -> subscriber.id))
                .toList();
        if (interested.isEmpty()) {
            deadLetterQueue.add(NO_SUBSCRIBER, event);
        }
        int delivered = 0;
        for (Subscriber subscriber : interested) {
            if (subscriber.offer(event)) {
                delivered++;
            } else {
                deadLetterQueue.add(subscriber.id, event);
            }
        }
        return delivered;
    }

    public List<String> poll(String subscriberId, int maxEvents) {
        Subscriber subscriber = subscribers.get(subscriberId);
        return subscriber == null ? List.of() : subscriber.take(maxEvents);
    }

    public int pending(String subscriberId) {
        Subscriber subscriber = subscribers.get(subscriberId);
        return subscriber == null ? -1 : subscriber.inbox.size();
    }

    public boolean setInboxLimit(String subscriberId, int limit) {
        Subscriber subscriber = subscribers.get(subscriberId);
        if (subscriber == null) {
            return false;
        }
        subscriber.limit = limit;
        return true;
    }

    public List<String> deadLetters(int maxEvents) {
        return deadLetterQueue.drain(maxEvents);
    }
}
