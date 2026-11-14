package coworking.vendors;

import static java.util.Objects.requireNonNull;

import coworking.vendors.VendorHttp.Answer;
import java.net.URI;
import java.time.Duration;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.regex.Pattern;

/** The vendor of the main building's rooms: what it speaks, and when to ask it again. */
public final class RoomVendor implements RoomSource {
    static final String NAME = "room-vendor";
    static final int MAX_REQUESTS = 3;
    static final Duration SHORT_WAIT = Duration.ofMillis(200);
    private static final int TOO_MANY_REQUESTS = 429;
    private static final int SERVER_ERROR = 500;
    private static final Pattern WHOLE_SECONDS = Pattern.compile("[0-9]{1,9}");
    private static final String OPEN = "open";

    private final URI availability;

    public RoomVendor(URI baseUrl) {
        this.availability = baseUrl.resolve("/v1/rooms/availability");
    }

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public List<Slot> openSlots(LocalDate day) throws VendorUnavailableException {
        URI uri = URI.create(availability + "?date=" + day);
        Answer answer = Retries.ask(() -> VendorHttp.get(uri), RoomVendor::waitBeforeRetry, MAX_REQUESTS);
        if (!answer.ok()) {
            throw new VendorUnavailableException(NAME + " answered " + answer.status());
        }
        return answer.as(Rooms.class, NAME).rooms().stream()
                .flatMap(room -> room.slots().stream()
                        .filter(RoomSlot::isOpen)
                        .map(slot -> new Slot(room.id(), slot.start(), slot.end(), NAME)))
                .toList();
    }

    /** How long to wait before asking again; empty when asking again will not help. */
    static Optional<Duration> waitBeforeRetry(Answer answer) {
        if (answer.status() == TOO_MANY_REQUESTS) {
            return Optional.of(answer.headers().firstValue("Retry-After")
                    .filter(WHOLE_SECONDS.asMatchPredicate())
                    .map(seconds -> Duration.ofSeconds(Long.parseLong(seconds)))
                    .orElse(SHORT_WAIT));
        }
        return answer.status() >= SERVER_ERROR ? Optional.of(SHORT_WAIT) : Optional.empty();
    }

    /** Its answer, as its API documents it. */
    record Rooms(List<Room> rooms) {
        Rooms {
            rooms = List.copyOf(rooms);
        }
    }

    record Room(String id, List<RoomSlot> slots) {
        Room {
            requireNonNull(id, "id");
            slots = List.copyOf(slots);
        }
    }

    /** A slot whose status is not open may leave out its times. */
    record RoomSlot(String status, String start, String end) {
        RoomSlot {
            requireNonNull(status, "status");
            if (status.equals(OPEN)) {
                requireNonNull(start, "start");
                requireNonNull(end, "end");
            }
        }

        boolean isOpen() {
            return status.equals(OPEN);
        }
    }
}
