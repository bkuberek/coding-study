package coworking.vendors;

import static java.util.Objects.requireNonNull;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.net.URI;
import java.time.Duration;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Optional;
import java.util.stream.Stream;

/** The vendor of the building next door, which says most things in the body of a 200. */
public final class AnnexVendor implements RoomSource {
    static final String NAME = "annex-vendor";
    static final int MAX_REQUESTS = 2;
    private static final String BUSY = "BUSY";
    private static final int MINUTES_PER_HOUR = 60;

    private final URI spaces;

    public AnnexVendor(URI baseUrl) {
        this.spaces = baseUrl.resolve("/v2/spaces/open");
    }

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public List<Slot> openSlots(LocalDate day) throws VendorUnavailableException {
        URI uri = URI.create(spaces + "?day=" + day.format(DateTimeFormatter.BASIC_ISO_DATE));
        AnnexAnswer answer = Retries.ask(() -> body(uri), AnnexVendor::waitBeforeRetry, MAX_REQUESTS);
        if (!answer.ok() || answer.result() == null) {
            throw new VendorUnavailableException(NAME + " gave no spaces: " + answer);
        }
        return answer.result().spaces().stream().flatMap(Space::slots).toList();
    }

    /** Its 5xx means down for maintenance, so any status but 2xx ends the asking. */
    private static AnnexAnswer body(URI uri) throws VendorUnavailableException {
        VendorHttp.Answer answer = VendorHttp.get(uri);
        if (!answer.ok()) {
            throw new VendorUnavailableException(NAME + " answered " + answer.status());
        }
        return answer.as(AnnexAnswer.class, NAME);
    }

    /** How long it asks you to wait before asking again; empty if it does not ask. */
    static Optional<Duration> waitBeforeRetry(AnnexAnswer answer) {
        Failure error = answer.error();
        if (answer.ok() || error == null || !error.code().equals(BUSY) || error.retryAfterMs() == null) {
            return Optional.empty();
        }
        return Optional.of(Duration.ofMillis((long) Math.ceil(error.retryAfterMs())));
    }

    /** Its answer, as its API documents it: a result when ok, an error when not. */
    record AnnexAnswer(Boolean ok, Spaces result, Failure error) {
        AnnexAnswer {
            requireNonNull(ok, "ok");
        }
    }

    record Spaces(List<Space> spaces) {
        Spaces {
            spaces = List.copyOf(spaces);
        }
    }

    record Space(String code, List<Window> open) {
        Space {
            requireNonNull(code, "code");
            open = List.copyOf(open);
        }

        Stream<Slot> slots() {
            return open.stream().map(window -> new Slot(
                    code, clock(window.fromMinute()), clock(window.fromMinute() + window.minutes()), NAME));
        }
    }

    /** Times come as minutes past midnight. */
    record Window(@JsonProperty("from_minute") Integer fromMinute, Integer minutes) {
        Window {
            requireNonNull(fromMinute, "from_minute");
            requireNonNull(minutes, "minutes");
        }
    }

    record Failure(String code, @JsonProperty("retry_after_ms") Double retryAfterMs) {
        Failure {
            requireNonNull(code, "code");
        }
    }

    private static String clock(int minutesPastMidnight) {
        return "%02d:%02d".formatted(minutesPastMidnight / MINUTES_PER_HOUR, minutesPastMidnight % MINUTES_PER_HOUR);
    }
}
