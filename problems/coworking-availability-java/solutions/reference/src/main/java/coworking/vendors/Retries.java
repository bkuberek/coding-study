package coworking.vendors;

import java.time.Duration;
import java.util.Optional;
import java.util.function.Function;

/** The loop both vendors share: it counts and waits, and each vendor's own rules say how long. */
final class Retries {
    private Retries() {}

    @FunctionalInterface
    interface Request<T> {
        T send() throws VendorUnavailableException;
    }

    /**
     * Asks until asking again will not help, or {@code maxRequests} are spent. {@code
     * waitBeforeRetry} reads an answer and gives the wait before asking again, or empty when
     * asking again will not help. The wait starts once the answer has arrived.
     */
    static <T> T ask(Request<T> request, Function<T, Optional<Duration>> waitBeforeRetry, int maxRequests)
            throws VendorUnavailableException {
        T answer = request.send();
        for (int sent = 1; sent < maxRequests; sent++) {
            Optional<Duration> wait = waitBeforeRetry.apply(answer);
            if (wait.isEmpty()) {
                break;
            }
            sleep(wait.get());
            answer = request.send();
        }
        return answer;
    }

    private static void sleep(Duration wait) throws VendorUnavailableException {
        try {
            Thread.sleep(wait);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            throw new VendorUnavailableException("stopped while waiting to ask again", interrupted);
        }
    }
}
