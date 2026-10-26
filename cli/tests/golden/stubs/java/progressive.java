// In-Memory Database. Statement: .statements/in-memory-db.md. Run: cstudy test in-memory-db

package practice.in_memory_db;

import java.util.*;

public class InMemoryDb {
    public InMemoryDb() {
    }

    // Level 1
    public void set(long timestamp, String key, String field, String value) {
        throw new UnsupportedOperationException("Not implemented");
    }

    // Level 1
    public String get(long timestamp, String key, String field) {
        throw new UnsupportedOperationException("Not implemented");
    }

    // Level 2
    public String[] scanByPrefix(long timestamp, String key, String prefix) {
        throw new UnsupportedOperationException("Not implemented");
    }
}
