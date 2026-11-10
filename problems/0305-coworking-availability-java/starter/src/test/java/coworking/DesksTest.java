package coworking;

import static coworking.App.json;
import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class DesksTest {
    private final App app = new App();

    @Test
    void theServiceAnswersItsHealthPath() throws Exception {
        assertEquals(200, app.get("/health").status());
    }

    @Test
    void aDayOnSaleAnswersItsCount() throws Exception {
        App.Answer expected = new App.Answer(200, json("""
                {"date": "2027-03-01", "available": 12}
                """));

        assertEquals(expected, app.get("/desks?date=2027-03-01"));
    }

    @Test
    void noDateIsABadRequest() throws Exception {
        App.Answer expected = new App.Answer(400, json("""
                {"error": "date is required"}
                """));

        assertEquals(expected, app.get("/desks"));
    }
}
