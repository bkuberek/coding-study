import java.util.*;

public class CloudStorage {
    /** A stored file; {@code owner} is null for files added without a user. */
    private record StoredFile(String name, long size, String owner) {
    }

    private static final class User {
        long capacity;
        long used;
        final Set<String> files = new HashSet<>();

        User(long capacity) {
            this.capacity = capacity;
        }

        boolean fits(long size) {
            return used + size <= capacity;
        }
    }

    private static final Comparator<StoredFile> LARGEST_FIRST =
            Comparator.comparingLong(StoredFile::size).reversed().thenComparing(StoredFile::name);

    private final Map<String, StoredFile> files = new HashMap<>();
    private final Map<String, User> users = new HashMap<>();
    private final Map<String, List<StoredFile>> backups = new HashMap<>();

    public CloudStorage() {
    }

    // Level 1
    public boolean addFile(long timestamp, String name, long size) {
        if (files.containsKey(name)) {
            return false;
        }
        store(new StoredFile(name, size, null));
        return true;
    }

    public long getFileSize(long timestamp, String name) {
        StoredFile file = files.get(name);
        return file == null ? -1 : file.size();
    }

    public long deleteFile(long timestamp, String name) {
        StoredFile file = files.get(name);
        if (file == null) {
            return -1;
        }
        discard(file);
        return file.size();
    }

    // Level 2
    public List<String> listLargest(long timestamp, String prefix, int limit) {
        return files.values().stream()
                .filter(file -> file.name().startsWith(prefix))
                .sorted(LARGEST_FIRST)
                .limit(limit)
                .map(file -> file.name() + "(" + file.size() + ")")
                .toList();
    }

    // Level 3
    public boolean addUser(long timestamp, String userId, long capacity) {
        if (users.containsKey(userId)) {
            return false;
        }
        users.put(userId, new User(capacity));
        return true;
    }

    public long addFileBy(long timestamp, String userId, String name, long size) {
        User user = users.get(userId);
        if (user == null || files.containsKey(name) || !user.fits(size)) {
            return -1;
        }
        store(new StoredFile(name, size, userId));
        return user.capacity - user.used;
    }

    public int updateCapacity(long timestamp, String userId, long capacity) {
        User user = users.get(userId);
        if (user == null) {
            return -1;
        }
        user.capacity = capacity;
        List<StoredFile> owned = ownedBy(user);
        owned.sort(LARGEST_FIRST);
        int removed = 0;
        for (StoredFile file : owned) {
            if (user.used <= capacity) {
                break;
            }
            discard(file);
            removed++;
        }
        return removed;
    }

    // Level 4
    public int backupUser(long timestamp, String userId) {
        User user = users.get(userId);
        if (user == null) {
            return -1;
        }
        List<StoredFile> saved = ownedBy(user);
        backups.put(userId, saved);
        return saved.size();
    }

    public int restoreUser(long timestamp, String userId) {
        User user = users.get(userId);
        if (user == null) {
            return -1;
        }
        ownedBy(user).forEach(this::discard);
        List<StoredFile> saved = new ArrayList<>(backups.getOrDefault(userId, List.of()));
        saved.sort(Comparator.comparing(StoredFile::name));
        int restored = 0;
        for (StoredFile file : saved) {
            if (!files.containsKey(file.name()) && user.fits(file.size())) {
                store(file);
                restored++;
            }
        }
        return restored;
    }

    private List<StoredFile> ownedBy(User user) {
        List<StoredFile> owned = new ArrayList<>();
        for (String name : user.files) {
            owned.add(files.get(name));
        }
        return owned;
    }

    private void store(StoredFile file) {
        files.put(file.name(), file);
        if (file.owner() != null) {
            User user = users.get(file.owner());
            user.used += file.size();
            user.files.add(file.name());
        }
    }

    private void discard(StoredFile file) {
        files.remove(file.name());
        if (file.owner() != null) {
            User user = users.get(file.owner());
            user.used -= file.size();
            user.files.remove(file.name());
        }
    }
}
