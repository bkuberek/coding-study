package coworking;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.time.LocalDate;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

class DaysTest {
    @Test
    void aRealDayIsThatDay() {
        assertEquals(Optional.of(LocalDate.of(2027, 3, 1)), Days.parse("2027-03-01"));
    }

    @Test
    void aLeapDayIsRealInALeapYear() {
        assertEquals(Optional.of(LocalDate.of(2028, 2, 29)), Days.parse("2028-02-29"));
    }

    @ParameterizedTest
    @ValueSource(strings = {
        "2027-02-30", "2027-02-29", "2027-13-01", "2027-3-1", "20270301", "+12027-03-01", "2027-03-01\n", "soon"
    })
    void namesNoDay(String text) {
        assertEquals(Optional.empty(), Days.parse(text));
    }
}
