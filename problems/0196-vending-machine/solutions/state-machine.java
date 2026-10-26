import java.util.*;

public class VendingMachine {
    private enum State { MAINTENANCE, IDLE, HAS_CREDIT }

    /** The coins inside the machine, by denomination; pays out exact change with the fewest coins. */
    private static final class CoinBox {
        private static final int IMPOSSIBLE = Integer.MAX_VALUE / 2;
        private final TreeMap<Integer, Integer> counts = new TreeMap<>(Comparator.reverseOrder());

        CoinBox(int[] denominations) {
            for (int coin : denominations) {
                counts.put(coin, 0);
            }
        }

        boolean accepts(int coin) {
            return counts.containsKey(coin);
        }

        void add(int coin, int count) {
            counts.merge(coin, count, Integer::sum);
        }

        /** Remove and return coins worth {@code amount}, or empty (changing nothing) when impossible. */
        Optional<List<Integer>> payOut(int amount) {
            Optional<List<Integer>> coins = plan(amount);
            coins.ifPresent(planned -> planned.forEach(coin -> add(coin, -1)));
            return coins;
        }

        /** Fewest coins; among those, as many of the largest coin as possible, then the next. */
        private Optional<List<Integer>> plan(int amount) {
            List<Map.Entry<Integer, Integer>> stock = new ArrayList<>(counts.entrySet());
            int n = stock.size();
            // fewest[i][a]: fewest coins making a from denominations i and smaller.
            int[][] fewest = new int[n + 1][amount + 1];
            for (int[] row : fewest) {
                Arrays.fill(row, IMPOSSIBLE);
            }
            fewest[n][0] = 0;
            for (int i = n - 1; i >= 0; i--) {
                int coin = stock.get(i).getKey();
                int available = stock.get(i).getValue();
                for (int a = 0; a <= amount; a++) {
                    for (int k = 0; k <= Math.min(available, a / coin); k++) {
                        fewest[i][a] = Math.min(fewest[i][a], k + fewest[i + 1][a - k * coin]);
                    }
                }
            }
            if (fewest[0][amount] >= IMPOSSIBLE) {
                return Optional.empty();
            }
            List<Integer> coins = new ArrayList<>();
            int remaining = amount;
            for (int i = 0; i < n; i++) {
                int coin = stock.get(i).getKey();
                for (int k = Math.min(stock.get(i).getValue(), remaining / coin); k >= 0; k--) {
                    if (k + fewest[i + 1][remaining - k * coin] == fewest[i][remaining]) {
                        coins.addAll(Collections.nCopies(k, coin));
                        remaining -= k * coin;
                        break;
                    }
                }
            }
            return Optional.of(coins);
        }
    }

    private static final class Slot {
        int price;
        int count;
    }

    private State state = State.MAINTENANCE;
    private final CoinBox coins;
    private final Map<String, Slot> slots = new HashMap<>();
    private int credit;
    private final List<Integer> tray = new ArrayList<>();

    public VendingMachine(int[] denominations) {
        coins = new CoinBox(denominations);
    }

    public boolean service(boolean enabled) {
        if (enabled && state == State.IDLE) {
            state = State.MAINTENANCE;
            return true;
        }
        if (!enabled && state == State.MAINTENANCE) {
            state = State.IDLE;
            return true;
        }
        return false;
    }

    public boolean stock(String slot, int price, int count) {
        if (state != State.MAINTENANCE) {
            return false;
        }
        Slot item = slots.computeIfAbsent(slot, s -> new Slot());
        item.price = price;
        item.count += count;
        return true;
    }

    public boolean loadCoins(int coin, int count) {
        if (state != State.MAINTENANCE || !coins.accepts(coin)) {
            return false;
        }
        coins.add(coin, count);
        return true;
    }

    public int insert(int coin) {
        if (state == State.MAINTENANCE || !coins.accepts(coin)) {
            tray.add(coin);
            return -1;
        }
        coins.add(coin, 1);
        credit += coin;
        state = State.HAS_CREDIT;
        return credit;
    }

    public String select(String slot) {
        if (state == State.MAINTENANCE) {
            return "OUT_OF_SERVICE";
        }
        Slot item = slots.get(slot);
        if (item == null) {
            return "UNKNOWN_SLOT";
        }
        if (item.count == 0) {
            return "SOLD_OUT";
        }
        if (credit < item.price) {
            return "INSUFFICIENT_CREDIT";
        }
        Optional<List<Integer>> change = coins.payOut(credit - item.price);
        if (change.isEmpty()) {
            return "NO_CHANGE";
        }
        item.count--;
        finish(change.get());
        return "DISPENSED";
    }

    public int refund() {
        if (state != State.HAS_CREDIT) {
            return 0;
        }
        int amount = credit;
        finish(coins.payOut(amount).orElse(List.of()));
        return amount;
    }

    public List<Integer> collect() {
        List<Integer> collected = new ArrayList<>(tray);
        collected.sort(Comparator.reverseOrder());
        tray.clear();
        return collected;
    }

    public String state() {
        return state.name();
    }

    public int stockOf(String slot) {
        Slot item = slots.get(slot);
        return item == null ? -1 : item.count;
    }

    /** Return change to the tray and end the transaction. */
    private void finish(List<Integer> change) {
        tray.addAll(change);
        credit = 0;
        state = State.IDLE;
    }
}
