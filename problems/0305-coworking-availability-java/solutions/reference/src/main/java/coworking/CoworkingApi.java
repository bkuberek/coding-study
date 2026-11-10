package coworking;

import coworking.vendors.RoomSource;
import java.net.URI;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

/** Every answer the API gives, from a request's method and target; no HTTP. */
public final class CoworkingApi {
    private static final String GET = "GET";

    private final DeskInventory desks;
    private final List<RoomSource> vendors;
    private final Map<String, Route> routes = Map.of(
            "/health", date -> new Reply(200, Map.of("status", "ok")),
            "/desks", this::desksOn,
            "/availability", this::availabilityOn);

    public CoworkingApi(DeskInventory desks, List<RoomSource> vendors) {
        this.desks = desks;
        this.vendors = List.copyOf(vendors);
    }

    public Reply answer(String method, URI target) {
        Route route = routes.get(target.getPath());
        if (route == null) {
            return Reply.error(404, "not found");
        }
        if (!method.equals(GET)) {
            return Reply.error(405, "method not allowed");
        }
        try {
            return route.answer(Query.value(target, "date"));
        } catch (Refused refused) {
            return refused.reply();
        }
    }

    private Reply desksOn(String text) throws Refused {
        DayOnSale day = onSale(text);
        return new Reply(200, new DeskCount(text, day.available()));
    }

    private Reply availabilityOn(String text) throws Refused {
        DayOnSale day = onSale(text);
        RoomAvailability rooms = RoomAvailability.of(day.date(), vendors);
        return new Reply(200, new Availability(text, new Desks(day.available()), rooms));
    }

    /** The day {@code text} names and its desks left, or Refused before a vendor hears of it. */
    private DayOnSale onSale(String text) throws Refused {
        if (text.isEmpty()) {
            throw new Refused(400, "date is required");
        }
        LocalDate date = Days.parse(text)
                .orElseThrow(() -> new Refused(400, "date must be a real day, as YYYY-MM-DD"));
        int available = desks.availableOn(text)
                .orElseThrow(() -> new Refused(404, "no desks on sale for that date"));
        return new DayOnSale(date, available);
    }

    @FunctionalInterface
    private interface Route {
        Reply answer(String date) throws Refused;
    }

    private record DayOnSale(LocalDate date, int available) {}

    record DeskCount(String date, int available) {}

    record Desks(int available) {}

    record Availability(String date, Desks desks, RoomAvailability rooms) {}

    /** A request this API will not answer for its date, with the reply that says why. */
    private static final class Refused extends Exception {
        private final transient Reply reply;

        Refused(int status, String error) {
            super(error, null, false, false);
            this.reply = Reply.error(status, error);
        }

        Reply reply() {
            return reply;
        }
    }
}
