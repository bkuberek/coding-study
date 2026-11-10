package coworking;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.Optional;
import java.util.regex.Pattern;

/** The one form a day takes in this API. */
final class Days {
    private static final Pattern DAY_FORM = Pattern.compile("[0-9]{4}-[0-9]{2}-[0-9]{2}");

    private Days() {}

    /**
     * The day {@code text} names, written YYYY-MM-DD; empty when it names no day in that form. The
     * form comes first: {@code LocalDate.parse} alone takes {@code +12027-03-01} as well.
     */
    static Optional<LocalDate> parse(String text) {
        if (!DAY_FORM.matcher(text).matches()) {
            return Optional.empty();
        }
        try {
            return Optional.of(LocalDate.parse(text));
        } catch (DateTimeParseException noSuchDay) {
            return Optional.empty();
        }
    }
}
