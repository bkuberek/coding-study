package coworking.vendors;

/** One slot a member can book, and the vendor a booking goes to. */
public record Slot(String room, String start, String end, String vendor) {}
