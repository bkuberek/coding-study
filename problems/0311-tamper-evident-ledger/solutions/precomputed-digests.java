import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.*;
import java.util.regex.Pattern;

public class Ledger {
    private static final byte[] GENESIS = new byte[32];
    private static final byte LEAF_PREFIX = 0x00;
    private static final byte NODE_PREFIX = 0x01;
    private static final Pattern HEX_DIGEST = Pattern.compile("[0-9a-f]{64}");

    private final Map<String, Batch> batches = new HashMap<>();
    private final Map<String, Chain> chains = new HashMap<>();

    private static byte[] sha256(byte[]... parts) {
        try {
            MessageDigest hash = MessageDigest.getInstance("SHA-256");
            for (byte[] part : parts) {
                hash.update(part);
            }
            return hash.digest();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    /** A field is its length in bytes (4 bytes, big-endian) and then its UTF-8 bytes. */
    private static byte[] encodeText(String value) {
        byte[] data = value.getBytes(StandardCharsets.UTF_8);
        return ByteBuffer.allocate(4 + data.length).putInt(data.length).put(data).array();
    }

    /** Drops trailing fractional zeros and a dangling point, and writes {@code -0} as {@code 0}. */
    private static String canonicalAmount(String amount) {
        String trimmed = amount;
        if (amount.contains(".")) {
            int end = amount.length();
            while (amount.charAt(end - 1) == '0') {
                end--;
            }
            if (amount.charAt(end - 1) == '.') {
                end--;
            }
            trimmed = amount.substring(0, end);
        }
        return trimmed.equals("-0") ? "0" : trimmed;
    }

    private static byte[] recordDigest(List<String> record) {
        return sha256(
                encodeText(record.get(0)),
                encodeText(record.get(1)),
                encodeText(record.get(2)),
                encodeText(canonicalAmount(record.get(3))));
    }

    private static byte[] leafDigest(byte[] digestOfRecord) {
        return sha256(new byte[] {LEAF_PREFIX}, digestOfRecord);
    }

    private static byte[] nodeDigest(byte[] left, byte[] right) {
        return sha256(new byte[] {NODE_PREFIX}, left, right);
    }

    private static String hex(byte[] bytes) {
        return HexFormat.of().formatHex(bytes);
    }

    /** Everything a batch can be asked is computed once, when it is built. */
    private static final class Batch {
        final List<byte[]> recordDigests = new ArrayList<>();
        final byte[] digest;
        private List<List<byte[]>> tree;

        Batch(List<List<String>> records) {
            for (List<String> record : records) {
                recordDigests.add(recordDigest(record));
            }
            digest = sha256(recordDigests.toArray(new byte[0][]));
        }

        /** The Merkle tree from the leaves up; a level of odd length is padded when it is paired. */
        List<List<byte[]>> levels() {
            if (tree == null) {
                List<byte[]> level = new ArrayList<>();
                for (byte[] digestOfRecord : recordDigests) {
                    level.add(leafDigest(digestOfRecord));
                }
                tree = new ArrayList<>();
                tree.add(level);
                while (level.size() > 1) {
                    List<byte[]> padded = padded(level);
                    List<byte[]> next = new ArrayList<>();
                    for (int i = 0; i < padded.size(); i += 2) {
                        next.add(nodeDigest(padded.get(i), padded.get(i + 1)));
                    }
                    level = next;
                    tree.add(level);
                }
            }
            return tree;
        }

        static List<byte[]> padded(List<byte[]> level) {
            if (level.size() % 2 == 0) {
                return level;
            }
            List<byte[]> copy = new ArrayList<>(level);
            copy.add(level.get(level.size() - 1));
            return copy;
        }

        byte[] root() {
            List<List<byte[]>> levels = levels();
            return levels.get(levels.size() - 1).get(0);
        }

        List<List<String>> proof(int recordIndex) {
            List<List<String>> steps = new ArrayList<>();
            List<List<byte[]>> levels = levels();
            int index = recordIndex;
            for (int depth = 0; depth < levels.size() - 1; depth++) {
                List<byte[]> padded = padded(levels.get(depth));
                int sibling = index ^ 1;
                steps.add(List.of(sibling < index ? "L" : "R", hex(padded.get(sibling))));
                index /= 2;
            }
            return steps;
        }
    }

    private static final class Chain {
        final int batchSize;
        List<List<String>> pending = new ArrayList<>();
        final List<Batch> batches = new ArrayList<>();
        final List<byte[]> digests = new ArrayList<>();

        Chain(int batchSize) {
            this.batchSize = batchSize;
        }

        void add(List<String> record) {
            pending.add(List.copyOf(record));
            if (pending.size() == batchSize) {
                Batch batch = new Batch(pending);
                pending = new ArrayList<>();
                batches.add(batch);
                digests.add(sha256(tip(), batch.digest));
            }
        }

        byte[] tip() {
            return digests.isEmpty() ? GENESIS : digests.get(digests.size() - 1);
        }
    }

    // Level 1
    public void addBatch(String name, List<List<String>> records) {
        batches.put(name, new Batch(records));
    }

    public String batchDigest(String name) {
        return hex(batches.get(name).digest);
    }

    public boolean sameBatch(String first, String second) {
        return Arrays.equals(batches.get(first).digest, batches.get(second).digest);
    }

    // Level 2
    public void newChain(String name, int batchSize) {
        chains.put(name, new Chain(batchSize));
    }

    public void addRecord(String name, List<String> record) {
        chains.get(name).add(record);
    }

    public int sealedCount(String name) {
        return chains.get(name).batches.size();
    }

    public String chainDigest(String name) {
        return hex(chains.get(name).tip());
    }

    public boolean sameChain(String first, String second) {
        return Arrays.equals(chains.get(first).tip(), chains.get(second).tip());
    }

    // Level 3
    /** The prefix digests agree up to some length and never again, so the length can be bisected. */
    public int commonPrefix(String first, String second) {
        List<byte[]> left = chains.get(first).digests;
        List<byte[]> right = chains.get(second).digests;
        int low = 0;
        int high = Math.min(left.size(), right.size());
        while (low < high) {
            int middle = (low + high + 1) / 2;
            if (Arrays.equals(left.get(middle - 1), right.get(middle - 1))) {
                low = middle;
            } else {
                high = middle - 1;
            }
        }
        return low;
    }

    // Level 4
    public String merkleRoot(String name, int batchIndex) {
        return hex(chains.get(name).batches.get(batchIndex).root());
    }

    public List<List<String>> proof(String name, int batchIndex, int recordIndex) {
        return chains.get(name).batches.get(batchIndex).proof(recordIndex);
    }

    public boolean verify(String root, List<String> record, List<List<String>> proof) {
        byte[] current = leafDigest(recordDigest(record));
        for (List<String> step : proof) {
            if (step.size() != 2
                    || !(step.get(0).equals("L") || step.get(0).equals("R"))
                    || !HEX_DIGEST.matcher(step.get(1)).matches()) {
                return false;
            }
            byte[] sibling = HexFormat.of().parseHex(step.get(1));
            current = step.get(0).equals("L") ? nodeDigest(sibling, current) : nodeDigest(current, sibling);
        }
        return hex(current).equals(root);
    }
}
