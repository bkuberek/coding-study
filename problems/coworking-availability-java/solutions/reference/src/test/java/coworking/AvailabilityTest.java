package coworking;

import static coworking.App.json;
import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

class AvailabilityTest {
    private final App app = new App();
    private final Vendors vendors = new Vendors();

    @AfterEach
    void resetTheVendors() throws Exception {
        vendors.reset();
    }

    private JsonNode roomsOn(String day) throws Exception {
        App.Answer answer = app.get("/availability?date=" + day);
        assertEquals(200, answer.status());
        return answer.body().get("rooms");
    }

    @Test
    void bothVendorsAnswerInOneList() throws Exception {
        JsonNode rooms = roomsOn("2027-03-08");

        assertEquals(5, rooms.get("slots").size());
        assertEquals(json("[]"), rooms.get("unavailable"));
    }

    @Test
    void aVendorThatIsDownCostsOnlyItsOwnSlots() throws Exception {
        vendors.setScenario("room-vendor", "outage");

        JsonNode rooms = roomsOn("2027-03-08");

        assertEquals(3, rooms.get("slots").size());
        assertEquals(json("[\"room-vendor\"]"), rooms.get("unavailable"));
    }

    @Test
    void bothVendorsDownStillAnswersTheDesks() throws Exception {
        vendors.setScenario("room-vendor", "outage");
        vendors.setScenario("annex-vendor", "maintenance");

        App.Answer expected = new App.Answer(200, json("""
                {
                  "date": "2027-03-08",
                  "desks": {"available": 20},
                  "rooms": {"slots": [], "unavailable": ["annex-vendor", "room-vendor"]}
                }
                """));

        assertEquals(expected, app.get("/availability?date=2027-03-08"));
    }
}
