import java.util.*;

public class StockSpanner {
    private final List<Integer> prices = new ArrayList<>();

    public StockSpanner() {
    }

    public int span(int price) {
        prices.add(price);
        int day = prices.size() - 1;
        while (day > 0 && prices.get(day - 1) <= price) {
            day--;
        }
        return prices.size() - day;
    }
}
