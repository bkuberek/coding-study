import java.util.*;
import java.util.function.Supplier;

public class ParkingLot {
    private static final long SECONDS_PER_HOUR = 3600;
    private static final long HOURS_PER_DAY = 24;
    private static final long DAILY_CAP_HOURS = 8;

    private enum SpotSize { SMALL, MEDIUM, LARGE }

    private enum VehicleType {
        MOTORCYCLE(List.of(SpotSize.SMALL, SpotSize.MEDIUM, SpotSize.LARGE), 100),
        CAR(List.of(SpotSize.MEDIUM, SpotSize.LARGE), 250),
        VAN(List.of(SpotSize.LARGE), 400);

        final List<SpotSize> fits; // smallest first
        final long hourlyRate; // cents

        VehicleType(List<SpotSize> fits, long hourlyRate) {
            this.fits = fits;
            this.hourlyRate = hourlyRate;
        }

        static Optional<VehicleType> parse(String name) {
            return Arrays.stream(values()).filter(type -> type.name().equals(name)).findFirst();
        }
    }

    private record Spot(int level, int index, SpotSize size) implements Comparable<Spot> {
        public int compareTo(Spot other) {
            return level != other.level ? Integer.compare(level, other.level) : Integer.compare(index, other.index);
        }

        String label() {
            return level + "-" + index;
        }
    }

    private record Ticket(String id, String plate, VehicleType vehicle, Spot spot, long parkedAt) {
    }

    private interface PricingPolicy {
        long fee(VehicleType vehicle, long parkedAt, long leftAt);
    }

    /** Started hours, at least one. */
    private static long billableHours(long parkedAt, long leftAt) {
        return Math.max(1, Math.ceilDiv(leftAt - parkedAt, SECONDS_PER_HOUR));
    }

    private static final class HourlyPricing implements PricingPolicy {
        public long fee(VehicleType vehicle, long parkedAt, long leftAt) {
            return billableHours(parkedAt, leftAt) * vehicle.hourlyRate;
        }
    }

    /** Hourly, but each started day costs at most DAILY_CAP_HOURS hours. */
    private static final class DailyCapPricing implements PricingPolicy {
        public long fee(VehicleType vehicle, long parkedAt, long leftAt) {
            long hours = billableHours(parkedAt, leftAt);
            long cap = DAILY_CAP_HOURS * vehicle.hourlyRate;
            return hours / HOURS_PER_DAY * cap + Math.min(hours % HOURS_PER_DAY * vehicle.hourlyRate, cap);
        }
    }

    private static final Map<String, Supplier<PricingPolicy>> PRICING_SCHEMES =
            Map.of("HOURLY", HourlyPricing::new, "DAILY_CAP", DailyCapPricing::new);

    /** Free spots per size; hands out the smallest fitting size, then the lowest level and index. */
    private static final class SpotAllocator {
        private final Map<SpotSize, PriorityQueue<Spot>> free = new EnumMap<>(SpotSize.class);

        SpotAllocator(List<String> layout) {
            for (SpotSize size : SpotSize.values()) {
                free.put(size, new PriorityQueue<>());
            }
            for (int level = 0; level < layout.size(); level++) {
                String row = layout.get(level);
                for (int index = 0; index < row.length(); index++) {
                    SpotSize size = switch (row.charAt(index)) {
                        case 'S' -> SpotSize.SMALL;
                        case 'M' -> SpotSize.MEDIUM;
                        default -> SpotSize.LARGE;
                    };
                    free.get(size).add(new Spot(level, index, size));
                }
            }
        }

        Optional<Spot> allocate(VehicleType vehicle) {
            for (SpotSize size : vehicle.fits) {
                Spot spot = free.get(size).poll();
                if (spot != null) {
                    return Optional.of(spot);
                }
            }
            return Optional.empty();
        }

        void release(Spot spot) {
            free.get(spot.size()).add(spot);
        }

        int freeCount(VehicleType vehicle) {
            return vehicle.fits.stream().mapToInt(size -> free.get(size).size()).sum();
        }
    }

    private final SpotAllocator allocator;
    private PricingPolicy pricing = new HourlyPricing();
    private final Map<String, Ticket> tickets = new HashMap<>();
    private final Map<String, Ticket> parked = new HashMap<>();
    private int issued;

    public ParkingLot(List<String> levels) {
        allocator = new SpotAllocator(levels);
    }

    public String park(long timestamp, String plate, String vehicleType) {
        Optional<VehicleType> vehicle = VehicleType.parse(vehicleType);
        if (vehicle.isEmpty() || parked.containsKey(plate)) {
            return "";
        }
        Optional<Spot> spot = allocator.allocate(vehicle.get());
        if (spot.isEmpty()) {
            return "";
        }
        issued++;
        Ticket ticket = new Ticket("T" + issued, plate, vehicle.get(), spot.get(), timestamp);
        tickets.put(ticket.id(), ticket);
        parked.put(plate, ticket);
        return ticket.id();
    }

    public long leave(long timestamp, String ticketId) {
        Ticket ticket = tickets.remove(ticketId);
        if (ticket == null) {
            return -1;
        }
        parked.remove(ticket.plate());
        allocator.release(ticket.spot());
        return pricing.fee(ticket.vehicle(), ticket.parkedAt(), timestamp);
    }

    public String locate(String plate) {
        Ticket ticket = parked.get(plate);
        return ticket == null ? "" : ticket.spot().label();
    }

    public int freeSpots(String vehicleType) {
        return VehicleType.parse(vehicleType).map(allocator::freeCount).orElse(-1);
    }

    public boolean setPricing(String scheme) {
        Supplier<PricingPolicy> create = PRICING_SCHEMES.get(scheme);
        if (create == null) {
            return false;
        }
        pricing = create.get();
        return true;
    }
}
