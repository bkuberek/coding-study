// Bounded Blocking Queue. Statement: .statements/bounded-blocking-queue.md.
// Run: cstudy test bounded-blocking-queue
// Concurrency: threads (platform and virtual)

package practice.bounded_blocking_queue;

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.locks.*;

public class BoundedBlockingQueue {
    public BoundedBlockingQueue(int capacity) {
    }

    public void put(int value) throws InterruptedException {
        throw new UnsupportedOperationException("Not implemented");
    }

    public int take() throws InterruptedException {
        throw new UnsupportedOperationException("Not implemented");
    }

    public int size() {
        throw new UnsupportedOperationException("Not implemented");
    }
}
