import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.CRC32;

// A hash map with separate chaining that doubles its buckets when the load factor passes 0.75.
//
// It hashes with CRC-32, the checksum zlib computes, so every run, in every language, fills the
// same buckets.
public class Chaining {
    static final double MAX_LOAD = 0.75;

    static final class Entry {
        final String key;
        int value;

        Entry(String key, int value) {
            this.key = key;
            this.value = value;
        }
    }

    static final class ChainedMap {
        List<List<Entry>> buckets = emptyBuckets(4);
        int size = 0;
        long moved = 0; // entries copied by every resize so far

        static List<List<Entry>> emptyBuckets(int count) {
            List<List<Entry>> buckets = new ArrayList<>(count);
            for (int i = 0; i < count; i++) {
                buckets.add(new ArrayList<>());
            }
            return buckets;
        }

        List<Entry> bucketOf(String key) {
            CRC32 crc = new CRC32();
            crc.update(key.getBytes(StandardCharsets.UTF_8));
            return buckets.get((int) (crc.getValue() % buckets.size()));
        }

        void put(String key, int value) {
            List<Entry> chain = bucketOf(key);
            for (Entry entry : chain) {
                if (entry.key.equals(key)) { // a collision is fine: compare the keys themselves
                    entry.value = value;
                    return;
                }
            }
            chain.add(new Entry(key, value));
            size += 1;
            if ((double) size / buckets.size() > MAX_LOAD) {
                resize(2 * buckets.size());
            }
        }

        Integer get(String key) {
            for (Entry entry : bucketOf(key)) {
                if (entry.key.equals(key)) {
                    return entry.value;
                }
            }
            return null;
        }

        void resize(int count) {
            List<Entry> entries = new ArrayList<>();
            buckets.forEach(entries::addAll);
            buckets = emptyBuckets(count);
            for (Entry entry : entries) {
                bucketOf(entry.key).add(entry);
            }
            moved += entries.size();
        }
    }

    public static void main(String[] args) {
        ChainedMap ages = new ChainedMap();
        String[] names = {"ada", "bo", "cy", "di"};
        for (int i = 0; i < names.length; i++) {
            ages.put(names[i], 30 + i);
            System.out.printf(
                    "put %s: %d entries in %d buckets%n", names[i], ages.size, ages.buckets.size());
        }
        System.out.println("get('cy') = " + ages.get("cy") + " | get('zed') = " + ages.get("zed"));

        for (int count : new int[] {1_000, 100_000}) {
            ChainedMap table = new ChainedMap();
            for (int number = 0; number < count; number++) {
                table.put("key" + number, number);
            }
            int longest = table.buckets.stream().mapToInt(List::size).max().orElse(0);
            System.out.printf(
                    "%7d puts: %6d buckets, %.2f moves per put, longest chain %d%n",
                    count, table.buckets.size(), (double) table.moved / count, longest);
        }
    }
}
