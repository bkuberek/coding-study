import java.util.*;

/**
 * A group of replicas of the same data. Each replica's state is a set of entries that only grow,
 * and merging is taking the larger value of every entry, so merges can happen in any order, any
 * number of times, and replicas that have seen the same updates hold the same state.
 */
public class Replicas {
    /** One replica's slot of a counter: what it added and what it took away, each with the change number at which it last grew. */
    private static final class Slot {
        long up, upAt, down, downAt;
    }

    private static final class Register {
        final String text;
        final long timestamp;
        final String writer;
        final long at;

        Register(String text, long timestamp, String writer, long at) {
            this.text = text;
            this.timestamp = timestamp;
            this.writer = writer;
            this.at = at;
        }

        boolean losesTo(long otherTimestamp, String otherWriter) {
            if (otherTimestamp != timestamp) {
                return otherTimestamp > timestamp;
            }
            return otherWriter.compareTo(writer) > 0;
        }
    }

    private static final class Tag {
        final long addedAt;
        boolean removed;
        long removedAt;

        Tag(long addedAt) {
            this.addedAt = addedAt;
        }
    }

    /**
     * The whole state of one replica. Every entry (a counter slot's up or down part, a register,
     * an add tag, a tombstone) only grows, and each one remembers the change number at which it
     * last grew, so a sync can pick the entries that changed after the last acknowledgement.
     */
    private static final class Replica {
        long clock;
        int adds;
        final Map<String, Map<String, Slot>> counters = new HashMap<>();
        final Map<String, Register> registers = new HashMap<>();
        final Map<String, Map<String, Map<String, Tag>>> sets = new HashMap<>();
        final Map<String, Long> acked = new HashMap<>();

        long tick() {
            return ++clock;
        }

        Slot slot(String counter, String owner) {
            return counters.computeIfAbsent(counter, k -> new HashMap<>()).computeIfAbsent(owner, k -> new Slot());
        }

        int total(String counter) {
            long sum = 0;
            for (Slot slot : counters.getOrDefault(counter, Map.of()).values()) {
                sum += slot.up - slot.down;
            }
            return (int) sum;
        }

        Map<String, Tag> tags(String setName, String element) {
            return sets.computeIfAbsent(setName, k -> new HashMap<>()).computeIfAbsent(element, k -> new HashMap<>());
        }

        boolean live(String setName, String element) {
            for (Tag tag : sets.getOrDefault(setName, Map.of()).getOrDefault(element, Map.of()).values()) {
                if (!tag.removed) {
                    return true;
                }
            }
            return false;
        }

        int size() {
            int count = registers.size();
            for (Map<String, Slot> slots : counters.values()) {
                for (Slot slot : slots.values()) {
                    count += (slot.up > 0 ? 1 : 0) + (slot.down > 0 ? 1 : 0);
                }
            }
            for (Map<String, Map<String, Tag>> elements : sets.values()) {
                for (Map<String, Tag> tags : elements.values()) {
                    for (Tag tag : tags.values()) {
                        count += tag.removed ? 2 : 1;
                    }
                }
            }
            return count;
        }

        /** Joins every entry of {@code source} that changed after {@code since}; {@code since = 0} is a full merge. */
        int absorb(Replica source, long since) {
            int sent = 0;
            for (Map.Entry<String, Map<String, Slot>> counter : source.counters.entrySet()) {
                for (Map.Entry<String, Slot> owned : counter.getValue().entrySet()) {
                    Slot theirs = owned.getValue();
                    Slot mine = slot(counter.getKey(), owned.getKey());
                    if (theirs.up > 0 && theirs.upAt > since) {
                        sent++;
                        if (theirs.up > mine.up) {
                            mine.up = theirs.up;
                            mine.upAt = tick();
                        }
                    }
                    if (theirs.down > 0 && theirs.downAt > since) {
                        sent++;
                        if (theirs.down > mine.down) {
                            mine.down = theirs.down;
                            mine.downAt = tick();
                        }
                    }
                }
            }
            for (Map.Entry<String, Register> named : source.registers.entrySet()) {
                Register theirs = named.getValue();
                if (theirs.at <= since) {
                    continue;
                }
                sent++;
                Register mine = registers.get(named.getKey());
                if (mine == null || mine.losesTo(theirs.timestamp, theirs.writer)) {
                    registers.put(named.getKey(), new Register(theirs.text, theirs.timestamp, theirs.writer, tick()));
                }
            }
            for (Map.Entry<String, Map<String, Map<String, Tag>>> set : source.sets.entrySet()) {
                for (Map.Entry<String, Map<String, Tag>> element : set.getValue().entrySet()) {
                    Map<String, Tag> mine = tags(set.getKey(), element.getKey());
                    for (Map.Entry<String, Tag> tag : element.getValue().entrySet()) {
                        sent += absorbTag(mine, tag.getKey(), tag.getValue(), since);
                    }
                }
            }
            return sent;
        }

        private int absorbTag(Map<String, Tag> mine, String tag, Tag theirs, long since) {
            int sent = 0;
            if (theirs.addedAt > since) {
                sent++;
                if (!mine.containsKey(tag)) {
                    mine.put(tag, new Tag(tick()));
                }
            }
            if (theirs.removed && theirs.removedAt > since) {
                sent++;
                Tag held = mine.computeIfAbsent(tag, k -> new Tag(tick()));
                if (!held.removed) {
                    held.removed = true;
                    held.removedAt = tick();
                }
            }
            return sent;
        }
    }

    private final Map<String, Replica> replicas = new HashMap<>();

    public Replicas(List<String> ids) {
        for (String id : ids) {
            replicas.put(id, new Replica());
        }
    }

    // Level 1
    public int increment(String replica, String counter, int amount) {
        Replica node = replicas.get(replica);
        Slot slot = node.slot(counter, replica);
        slot.up += amount;
        slot.upAt = node.tick();
        return node.total(counter);
    }

    public int decrement(String replica, String counter, int amount) {
        Replica node = replicas.get(replica);
        Slot slot = node.slot(counter, replica);
        slot.down += amount;
        slot.downAt = node.tick();
        return node.total(counter);
    }

    public int value(String replica, String counter) {
        return replicas.get(replica).total(counter);
    }

    public void merge(String source, String target) {
        replicas.get(target).absorb(replicas.get(source), 0);
    }

    // Level 2
    public boolean write(String replica, String register, String text, long timestamp) {
        Replica node = replicas.get(replica);
        Register current = node.registers.get(register);
        if (current != null && !current.losesTo(timestamp, replica)) {
            return false;
        }
        node.registers.put(register, new Register(text, timestamp, replica, node.tick()));
        return true;
    }

    public String read(String replica, String register) {
        Register current = replicas.get(replica).registers.get(register);
        return current == null ? "" : current.text;
    }

    // Level 3
    public String add(String replica, String setName, String element) {
        Replica node = replicas.get(replica);
        node.adds++;
        String tag = replica + ":" + node.adds;
        node.tags(setName, element).put(tag, new Tag(node.tick()));
        return tag;
    }

    public int remove(String replica, String setName, String element) {
        Replica node = replicas.get(replica);
        int removed = 0;
        for (Tag tag : node.sets.getOrDefault(setName, Map.of()).getOrDefault(element, Map.of()).values()) {
            if (!tag.removed) {
                tag.removed = true;
                tag.removedAt = node.tick();
                removed++;
            }
        }
        return removed;
    }

    public boolean contains(String replica, String setName, String element) {
        return replicas.get(replica).live(setName, element);
    }

    public List<String> elements(String replica, String setName) {
        Replica node = replicas.get(replica);
        List<String> present = new ArrayList<>();
        for (String element : node.sets.getOrDefault(setName, Map.of()).keySet()) {
            if (node.live(setName, element)) {
                present.add(element);
            }
        }
        Collections.sort(present);
        return present;
    }

    // Level 4
    public int sync(String source, String target) {
        Replica sender = replicas.get(source);
        int sent = replicas.get(target).absorb(sender, sender.acked.getOrDefault(target, 0L));
        sender.acked.put(target, sender.clock);
        return sent;
    }

    public int stateSize(String replica) {
        return replicas.get(replica).size();
    }
}
