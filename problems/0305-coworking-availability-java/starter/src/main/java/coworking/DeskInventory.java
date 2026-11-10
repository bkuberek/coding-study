package coworking;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.OptionalInt;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

/** The hot desks the space holds itself: how many are left on each day it sells. */
public final class DeskInventory {
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final TypeReference<Map<String, Integer>> COUNTS_BY_DAY = new TypeReference<>() {};

    private final Map<String, Integer> byDay;

    public DeskInventory(Map<String, Integer> byDay) {
        this.byDay = Map.copyOf(byDay);
    }

    public static DeskInventory fromFile(Path path) throws IOException {
        return new DeskInventory(JSON.readValue(Files.readString(path), COUNTS_BY_DAY));
    }

    /** Desks left on {@code day}, written YYYY-MM-DD; empty when it is not on sale. */
    public OptionalInt availableOn(String day) {
        Integer left = byDay.get(day);
        return left == null ? OptionalInt.empty() : OptionalInt.of(left);
    }
}
