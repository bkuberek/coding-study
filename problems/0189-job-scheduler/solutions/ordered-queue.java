import java.util.*;

public class JobScheduler {
    private enum Status { QUEUED, RUNNING, DONE, FAILED, CANCELLED }

    private static final class Job {
        final String id;
        final String tenant;
        final int priority;
        final int sequence;
        final List<String> dependsOn;
        final List<String> dependents = new ArrayList<>();
        Status status = Status.QUEUED;
        long notBefore;
        int failures;

        Job(String id, String tenant, int priority, int sequence, List<String> dependsOn) {
            this.id = id;
            this.tenant = tenant;
            this.priority = priority;
            this.sequence = sequence;
            this.dependsOn = dependsOn;
        }
    }

    private record RateLimit(int limit, long window) {
    }

    private record RetryPolicy(int maxRetries, long baseDelay) {
        static final RetryPolicy NONE = new RetryPolicy(0, 0);
    }

    /** Queue order: higher priority first, then earlier submission. */
    private static final Comparator<Job> QUEUE_ORDER =
            Comparator.comparingInt((Job job) -> -job.priority).thenComparingInt(job -> job.sequence);

    private final Map<String, Job> jobs = new HashMap<>();
    private final TreeSet<Job> queue = new TreeSet<>(QUEUE_ORDER);
    /** Tenant to start times; one start per call, so each list is strictly ascending. */
    private final Map<String, List<Long>> starts = new HashMap<>();
    private final Map<String, RateLimit> limits = new HashMap<>();
    private final Map<String, RetryPolicy> policies = new HashMap<>();

    public JobScheduler() {
    }

    // Level 1
    public boolean submit(long timestamp, String jobId, String tenant, int priority) {
        return submitAfter(timestamp, jobId, tenant, priority, List.of());
    }

    public String runNext(long timestamp) {
        for (Job job : queue) {
            if (canStart(job, timestamp)) {
                queue.remove(job);
                job.status = Status.RUNNING;
                starts.computeIfAbsent(job.tenant, tenant -> new ArrayList<>()).add(timestamp);
                return job.id;
            }
        }
        return "";
    }

    public String status(long timestamp, String jobId) {
        Job job = jobs.get(jobId);
        return job == null ? "" : job.status.name();
    }

    public int queued(long timestamp) {
        return queue.size();
    }

    // Level 2
    public void setRateLimit(long timestamp, String tenant, int limit, long windowMs) {
        limits.put(tenant, new RateLimit(limit, windowMs));
    }

    // Level 3
    public void setRetryPolicy(long timestamp, String tenant, int maxRetries, long baseDelayMs) {
        policies.put(tenant, new RetryPolicy(maxRetries, baseDelayMs));
    }

    public boolean complete(long timestamp, String jobId) {
        Job job = jobs.get(jobId);
        if (job == null || job.status != Status.RUNNING) {
            return false;
        }
        job.status = Status.DONE;
        return true;
    }

    public long fail(long timestamp, String jobId) {
        Job job = jobs.get(jobId);
        if (job == null || job.status != Status.RUNNING) {
            return -1;
        }
        job.failures++;
        RetryPolicy policy = policies.getOrDefault(job.tenant, RetryPolicy.NONE);
        if (job.failures > policy.maxRetries()) {
            job.status = Status.FAILED;
            cancelDependents(job);
            return 0;
        }
        job.notBefore = timestamp + (policy.baseDelay() << (job.failures - 1));
        enqueue(job);
        return job.notBefore;
    }

    // Level 4
    public boolean submitAfter(long timestamp, String jobId, String tenant, int priority, List<String> dependsOn) {
        if (jobs.containsKey(jobId)) {
            return false;
        }
        for (String dependency : dependsOn) {
            Job found = jobs.get(dependency);
            if (found == null || found.status == Status.FAILED || found.status == Status.CANCELLED) {
                return false;
            }
        }
        Job job = new Job(jobId, tenant, priority, jobs.size(), List.copyOf(dependsOn));
        jobs.put(jobId, job);
        for (String dependency : dependsOn) {
            jobs.get(dependency).dependents.add(jobId);
        }
        enqueue(job);
        return true;
    }

    public int cancel(long timestamp, String jobId) {
        Job job = jobs.get(jobId);
        if (job == null || job.status != Status.QUEUED) {
            return 0;
        }
        queue.remove(job);
        job.status = Status.CANCELLED;
        return 1 + cancelDependents(job);
    }

    private boolean canStart(Job job, long timestamp) {
        if (job.notBefore > timestamp) {
            return false;
        }
        for (String dependency : job.dependsOn) {
            if (jobs.get(dependency).status != Status.DONE) {
                return false;
            }
        }
        RateLimit limit = limits.get(job.tenant);
        if (limit == null) {
            return true;
        }
        List<Long> tenantStarts = starts.getOrDefault(job.tenant, List.of());
        int found = Collections.binarySearch(tenantStarts, timestamp - limit.window());
        int firstInWindow = found >= 0 ? found + 1 : -(found + 1);
        return tenantStarts.size() - firstInWindow < limit.limit();
    }

    /** Cancel every queued job that waits, directly or not, on {@code job}; return how many. */
    private int cancelDependents(Job job) {
        int cancelled = 0;
        Deque<String> pending = new ArrayDeque<>(job.dependents);
        while (!pending.isEmpty()) {
            Job dependent = jobs.get(pending.pop());
            if (dependent.status == Status.QUEUED) {
                queue.remove(dependent);
                dependent.status = Status.CANCELLED;
                cancelled++;
                pending.addAll(dependent.dependents);
            }
        }
        return cancelled;
    }

    private void enqueue(Job job) {
        job.status = Status.QUEUED;
        queue.add(job);
    }
}
