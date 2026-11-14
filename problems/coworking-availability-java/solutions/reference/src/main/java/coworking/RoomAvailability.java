package coworking;

import coworking.vendors.RoomSource;
import coworking.vendors.Slot;
import coworking.vendors.VendorUnavailableException;
import java.lang.System.Logger.Level;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

/** One answer from any number of vendors, none of which can take another down. */
public record RoomAvailability(List<Slot> slots, List<String> unavailable) {
    private static final System.Logger LOG = System.getLogger(RoomAvailability.class.getName());
    private static final Comparator<Slot> BY_START_THEN_ROOM =
            Comparator.comparing(Slot::start).thenComparing(Slot::room);

    /**
     * Asks every vendor at once, each on a virtual thread of its own, and waits for them all; one
     * with no usable answer goes in {@code unavailable}. Any other exception is a bug, and raises.
     */
    public static RoomAvailability of(LocalDate day, List<RoomSource> vendors) {
        Map<String, Future<List<Slot>>> asked = new LinkedHashMap<>();
        try (ExecutorService perVendor = Executors.newVirtualThreadPerTaskExecutor()) {
            for (RoomSource vendor : vendors) {
                asked.put(vendor.name(), perVendor.submit(() -> vendor.openSlots(day)));
            }
        }
        List<Slot> slots = new ArrayList<>();
        List<String> unavailable = new ArrayList<>();
        asked.forEach((name, answer) -> {
            switch (answer.state()) {
                case SUCCESS -> slots.addAll(answer.resultNow());
                case FAILED -> {
                    if (!(answer.exceptionNow() instanceof VendorUnavailableException reason)) {
                        throw new IllegalStateException("asking " + name, answer.exceptionNow());
                    }
                    LOG.log(Level.WARNING, "{0} is unavailable: {1}", name, reason.getMessage());
                    unavailable.add(name);
                }
                default -> throw new IllegalStateException(name + " was not asked: " + answer.state());
            }
        });
        slots.sort(BY_START_THEN_ROOM);
        unavailable.sort(Comparator.naturalOrder());
        return new RoomAvailability(List.copyOf(slots), List.copyOf(unavailable));
    }
}
