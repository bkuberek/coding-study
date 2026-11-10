package coworking.vendors;

import static org.junit.jupiter.api.Assertions.assertEquals;

import coworking.vendors.AnnexVendor.AnnexAnswer;
import coworking.vendors.AnnexVendor.Failure;
import coworking.vendors.AnnexVendor.Spaces;
import coworking.vendors.VendorHttp.Answer;
import java.net.http.HttpHeaders;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.junit.jupiter.params.provider.ValueSource;

class RetriesTest {
    private static Answer answer(int status, String... retryAfter) {
        Map<String, List<String>> headers = retryAfter.length == 0 ? Map.of() : Map.of("Retry-After", List.of(retryAfter));
        return new Answer(status, HttpHeaders.of(headers, (name, value) -> true), new byte[0]);
    }

    @Test
    void a429WaitsAsLongAsItSays() {
        assertEquals(Optional.of(Duration.ofSeconds(2)), RoomVendor.waitBeforeRetry(answer(429, "2")));
    }

    static Stream<Answer> aLittleWait() {
        return Stream.of(answer(429), answer(429, "soon"), answer(429, "-1"), answer(500), answer(503));
    }

    @ParameterizedTest
    @MethodSource("aLittleWait")
    void waitsALittle(Answer found) {
        assertEquals(Optional.of(RoomVendor.SHORT_WAIT), RoomVendor.waitBeforeRetry(found));
    }

    @ParameterizedTest
    @ValueSource(ints = {200, 400, 403, 404})
    void askingTheRoomVendorAgainWillNotHelp(int status) {
        assertEquals(Optional.empty(), RoomVendor.waitBeforeRetry(answer(status)));
    }

    @Test
    void busyWaitsAsManyMillisecondsAsItSays() {
        AnnexAnswer busy = new AnnexAnswer(false, null, new Failure("BUSY", 1500.0));

        assertEquals(Optional.of(Duration.ofMillis(1500)), AnnexVendor.waitBeforeRetry(busy));
    }

    static Stream<AnnexAnswer> noWait() {
        return Stream.of(
                new AnnexAnswer(false, null, new Failure("DAY_CLOSED", null)),
                new AnnexAnswer(false, null, new Failure("BUSY", null)),
                new AnnexAnswer(true, new Spaces(List.of()), null));
    }

    @ParameterizedTest
    @MethodSource("noWait")
    void askingTheAnnexAgainWillNotHelp(AnnexAnswer found) {
        assertEquals(Optional.empty(), AnnexVendor.waitBeforeRetry(found));
    }
}
