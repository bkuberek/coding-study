import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.*;

/**
 * Objects are bytes filed under the SHA-256 digest of those bytes. Every read hashes what it finds
 * again, so a damaged object reads as a missing one. Folders and manifests are objects that list
 * other objects by address, and refs name the objects the collector keeps.
 */
public class ContentStore {
    private static final int FIXED_SIZE = 64;
    private static final int WINDOW = 16;
    private static final long BASE = 257;
    private static final long MODULUS = 1_000_000_007L;
    private static final int MIN_CHUNK = 32;
    private static final int MAX_CHUNK = 256;
    private static final long DIVISOR = 64;
    private static final Set<String> KINDS = Set.of("blob", "tree", "manifest");

    private record Entry(String kind, String address) {}

    private record Change(String path, String op) {}

    private static final class Damaged extends RuntimeException {
        Damaged(String address) {
            super(address);
        }
    }

    private final Map<String, byte[]> objects = new HashMap<>();
    private final Map<String, Long> fileBytes = new HashMap<>(Map.of("fixed", 0L, "cdc", 0L));
    private final Map<String, Map<String, Integer>> chunks =
            new HashMap<>(Map.of("fixed", new HashMap<>(), "cdc", new HashMap<>()));
    private final Map<String, Entry> refs = new HashMap<>();

    private static String addressOf(byte[] data) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(data));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private static byte[] utf8(String text) {
        return text.getBytes(StandardCharsets.UTF_8);
    }

    private static List<String> lines(byte[] data) {
        String text = new String(data, StandardCharsets.UTF_8);
        if (text.isEmpty()) {
            return List.of();
        }
        return List.of(text.substring(0, text.length() - 1).split("\n", -1));
    }

    private String write(byte[] data) {
        String address = addressOf(data);
        if (read(address) == null) {
            objects.put(address, data);
        }
        return address;
    }

    private byte[] read(String address) {
        byte[] data = objects.get(address);
        return data != null && addressOf(data).equals(address) ? data : null;
    }

    // Level 1
    public String put(String data) {
        return write(utf8(data));
    }

    public String get(String address) {
        byte[] data = read(address);
        return data == null ? "" : new String(data, StandardCharsets.UTF_8);
    }

    public String check(String address) {
        if (!objects.containsKey(address)) {
            return "missing";
        }
        return read(address) == null ? "damaged" : "ok";
    }

    public boolean damage(String address, String data) {
        if (!objects.containsKey(address)) {
            return false;
        }
        objects.put(address, utf8(data));
        return true;
    }

    public int count() {
        return objects.size();
    }

    public int bytesStored() {
        int total = 0;
        for (byte[] data : objects.values()) {
            total += data.length;
        }
        return total;
    }

    // Level 2
    public String snapshot(List<List<String>> files) {
        List<Map.Entry<List<String>, String>> split = new ArrayList<>();
        for (List<String> file : files) {
            split.add(Map.entry(List.of(file.get(0).split("/", -1)), file.get(1)));
        }
        return folder(split);
    }

    private String folder(List<Map.Entry<List<String>, String>> files) {
        TreeMap<String, Entry> entries = new TreeMap<>();
        Map<String, List<Map.Entry<List<String>, String>>> below = new LinkedHashMap<>();
        for (Map.Entry<List<String>, String> file : files) {
            List<String> names = file.getKey();
            if (names.size() == 1) {
                entries.put(names.get(0), new Entry("blob", put(file.getValue())));
            } else {
                below.computeIfAbsent(names.get(0), name -> new ArrayList<>())
                        .add(Map.entry(names.subList(1, names.size()), file.getValue()));
            }
        }
        for (Map.Entry<String, List<Map.Entry<List<String>, String>>> inner : below.entrySet()) {
            entries.put(inner.getKey(), new Entry("tree", folder(inner.getValue())));
        }
        StringBuilder text = new StringBuilder();
        for (Map.Entry<String, Entry> entry : entries.entrySet()) {
            Entry value = entry.getValue();
            text.append(value.kind()).append(' ').append(value.address()).append(' ');
            text.append(entry.getKey()).append('\n');
        }
        return put(text.toString());
    }

    private Map<String, Entry> openTree(String address) {
        byte[] data = read(address);
        if (data == null) {
            throw new Damaged(address);
        }
        Map<String, Entry> entries = new HashMap<>();
        for (String line : lines(data)) {
            entries.put(line.substring(70), new Entry(line.substring(0, 4), line.substring(5, 69)));
        }
        return entries;
    }

    public String readPath(String root, String path) {
        Entry entry = new Entry("tree", root);
        try {
            for (String name : path.split("/", -1)) {
                if (!entry.kind().equals("tree")) {
                    return "";
                }
                entry = openTree(entry.address()).get(name);
                if (entry == null) {
                    return "";
                }
            }
        } catch (Damaged e) {
            return "";
        }
        return entry.kind().equals("blob") ? get(entry.address()) : "";
    }

    public List<String> diff(String oldRoot, String newRoot) {
        List<Change> changes = new ArrayList<>();
        try {
            compare("", oldRoot, newRoot, changes);
        } catch (Damaged e) {
            return new ArrayList<>();
        }
        changes.sort(Comparator.comparing(Change::path));
        List<String> result = new ArrayList<>();
        for (Change change : changes) {
            result.add(change.op() + " " + change.path());
        }
        return result;
    }

    private void compare(String prefix, String oldTree, String newTree, List<Change> changes) {
        if (oldTree.equals(newTree)) {
            return;
        }
        Map<String, Entry> before = openTree(oldTree);
        Map<String, Entry> after = openTree(newTree);
        Set<String> names = new HashSet<>(before.keySet());
        names.addAll(after.keySet());
        for (String name : names) {
            String path = prefix + name;
            Entry was = before.get(name);
            Entry now = after.get(name);
            if (Objects.equals(was, now)) {
                continue;
            }
            if (was != null && now != null && was.kind().equals(now.kind())) {
                if (was.kind().equals("blob")) {
                    changes.add(new Change(path, "M"));
                } else {
                    compare(path + "/", was.address(), now.address(), changes);
                }
                continue;
            }
            if (was != null) {
                listFiles("D", path, was, changes);
            }
            if (now != null) {
                listFiles("A", path, now, changes);
            }
        }
    }

    private void listFiles(String op, String path, Entry entry, List<Change> changes) {
        if (entry.kind().equals("blob")) {
            changes.add(new Change(path, op));
            return;
        }
        for (Map.Entry<String, Entry> inner : openTree(entry.address()).entrySet()) {
            listFiles(op, path + "/" + inner.getKey(), inner.getValue(), changes);
        }
    }

    // Level 3
    private static List<Integer> fixedSizes(int length) {
        List<Integer> sizes = new ArrayList<>();
        for (int start = 0; start < length; start += FIXED_SIZE) {
            sizes.add(Math.min(FIXED_SIZE, length - start));
        }
        return sizes;
    }

    /** Content-defined cuts: a rolling hash of the last 16 bytes, rolled once per byte. */
    private static List<Integer> cdcSizes(byte[] data) {
        long leavingWeight = 1;
        for (int i = 0; i < WINDOW - 1; i++) {
            leavingWeight = leavingWeight * BASE % MODULUS;
        }
        List<Integer> sizes = new ArrayList<>();
        long windowHash = 0;
        int start = 0;
        for (int index = 0; index < data.length; index++) {
            if (index >= WINDOW) {
                long leaving = Byte.toUnsignedLong(data[index - WINDOW]) * leavingWeight;
                windowHash = Math.floorMod(windowHash - leaving, MODULUS);
            }
            windowHash = (windowHash * BASE + Byte.toUnsignedLong(data[index])) % MODULUS;
            int length = index - start + 1;
            if (length == MAX_CHUNK || (length >= MIN_CHUNK && windowHash % DIVISOR == 0)) {
                sizes.add(length);
                start = index + 1;
            }
        }
        if (start < data.length) {
            sizes.add(data.length - start);
        }
        return sizes;
    }

    public List<Integer> chunkSizes(String data, String method) {
        byte[] raw = utf8(data);
        return method.equals("fixed") ? fixedSizes(raw.length) : cdcSizes(raw);
    }

    public String putFile(String data, String method) {
        byte[] raw = utf8(data);
        Map<String, Integer> seen = chunks.get(method);
        StringBuilder manifest = new StringBuilder();
        int start = 0;
        for (int size : chunkSizes(data, method)) {
            String address = write(Arrays.copyOfRange(raw, start, start + size));
            seen.put(address, size);
            manifest.append(address).append('\n');
            start += size;
        }
        fileBytes.merge(method, (long) raw.length, Long::sum);
        return put(manifest.toString());
    }

    public String readFile(String manifest) {
        byte[] listing = read(manifest);
        if (listing == null) {
            return "";
        }
        ByteArrayOutputStream parts = new ByteArrayOutputStream();
        for (String address : lines(listing)) {
            byte[] chunk = read(address);
            if (chunk == null) {
                return "";
            }
            parts.writeBytes(chunk);
        }
        return parts.toString(StandardCharsets.UTF_8);
    }

    public double dedupRatio(String method) {
        long stored = 0;
        for (int size : chunks.get(method).values()) {
            stored += size;
        }
        return stored == 0 ? 0.0 : (double) fileBytes.get(method) / stored;
    }

    // Level 4
    public boolean setRef(String name, String kind, String address) {
        if (!KINDS.contains(kind) || !objects.containsKey(address)) {
            return false;
        }
        refs.put(name, new Entry(kind, address));
        return true;
    }

    public String getRef(String name) {
        Entry entry = refs.get(name);
        return entry == null ? "" : entry.address();
    }

    public boolean deleteRef(String name) {
        return refs.remove(name) != null;
    }

    public int collectGarbage() {
        Set<String> live;
        try {
            live = mark();
        } catch (Damaged e) {
            return -1;
        }
        int freed = 0;
        Iterator<Map.Entry<String, byte[]>> stored = objects.entrySet().iterator();
        while (stored.hasNext()) {
            Map.Entry<String, byte[]> object = stored.next();
            if (!live.contains(object.getKey())) {
                freed += object.getValue().length;
                stored.remove();
            }
        }
        return freed;
    }

    private Set<String> mark() {
        Set<String> live = new HashSet<>();
        Set<Entry> visited = new HashSet<>();
        Deque<Entry> pending = new ArrayDeque<>(refs.values());
        while (!pending.isEmpty()) {
            Entry entry = pending.pop();
            if (!visited.add(entry)) {
                continue;
            }
            live.add(entry.address());
            if (entry.kind().equals("tree")) {
                pending.addAll(openTree(entry.address()).values());
            } else if (entry.kind().equals("manifest")) {
                byte[] listing = read(entry.address());
                if (listing == null) {
                    throw new Damaged(entry.address());
                }
                for (String address : lines(listing)) {
                    pending.push(new Entry("blob", address));
                }
            }
        }
        return live;
    }
}
