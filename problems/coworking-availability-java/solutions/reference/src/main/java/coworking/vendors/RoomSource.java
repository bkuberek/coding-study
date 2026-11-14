package coworking.vendors;

import java.time.LocalDate;
import java.util.List;

/** The seam between the API and its vendors: what every vendor looks like. */
public interface RoomSource {
    String name();

    /**
     * What can be booked on {@code day}.
     *
     * @throws VendorUnavailableException when the vendor gives no usable answer
     */
    List<Slot> openSlots(LocalDate day) throws VendorUnavailableException;
}
