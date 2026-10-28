package cs.runner;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonPrimitive;
import cs.support.GraphNode;
import cs.support.ListNode;
import cs.support.TreeNode;
import java.lang.reflect.Array;
import java.math.BigDecimal;
import java.time.DateTimeException;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;
import java.util.regex.Pattern;

/**
 * JSON values to JVM values and back, driven by the DSL type (the mapping table). A decimal is
 * encoded in canonical form (docs/specs/problem-format.md#decimal-and-date), so the CLI compares
 * it as plain text.
 */
final class Values {
    private static final Pattern DECIMAL_TEXT = Pattern.compile("-?(0|[1-9][0-9]*)(\\.[0-9]+)?");
    private static final Pattern DATE_TEXT = Pattern.compile("[0-9]{4}-[0-9]{2}-[0-9]{2}");

    private Values() {
    }

    /** A fresh JVM value for a parameter; a malformed value is a bad request. */
    static Object decode(DslType type, JsonElement json) {
        return switch (type) {
            case DslType.Scalar scalar -> decodeScalar(scalar, json);
            case DslType.ArrayOf array -> decodeArray(array, json);
            case DslType.ListOf list -> decodeList(list, json);
            case DslType.Node node -> decodeNode(node, json);
        };
    }

    static int decodeInt(JsonElement json) {
        return exact(json, "int", BigDecimal::intValueExact);
    }

    static JsonElement encode(DslType type, Object value) throws InvalidOutputException {
        return switch (type) {
            case DslType.Scalar scalar -> encodeScalar(scalar, value);
            case DslType.ArrayOf array -> encodeArray(array, value);
            case DslType.ListOf list -> encodeList(list, value);
            case DslType.Node node -> encodeNode(node, value);
        };
    }

    private static Object decodeScalar(DslType.Scalar type, JsonElement json) {
        return switch (type.kind()) {
            case INT -> decodeInt(json);
            case LONG -> exact(json, "long", BigDecimal::longValueExact);
            case DOUBLE -> number(json, "double").getAsDouble();
            case BOOL -> {
                if (!Json.isBoolean(json)) {
                    throw malformed(type, json);
                }
                yield json.getAsBoolean();
            }
            case STRING -> string(type, json);
            case CHAR -> {
                String text = string(type, json);
                if (text.length() != 1) {
                    throw malformed(type, json);
                }
                yield text.charAt(0);
            }
            case DECIMAL -> new BigDecimal(matching(DECIMAL_TEXT, string(type, json), type, json));
            case DATE -> decodeDate(type, json);
        };
    }

    private static LocalDate decodeDate(DslType.Scalar type, JsonElement json) {
        String text = matching(DATE_TEXT, string(type, json), type, json);
        try {
            LocalDate day = LocalDate.parse(text);
            if (day.getYear() >= 1) {
                return day;
            }
        } catch (DateTimeException error) {
            // falls through to the malformed value below
        }
        throw malformed(type, json);
    }

    private static String matching(Pattern pattern, String text, DslType type, JsonElement json) {
        if (!pattern.matcher(text).matches()) {
            throw malformed(type, json);
        }
        return text;
    }

    private static Object decodeArray(DslType.ArrayOf type, JsonElement json) {
        JsonArray items = Json.asArray(json, type.toString());
        Object array = Array.newInstance(type.element().jvmClass(), items.size());
        for (int index = 0; index < items.size(); index++) {
            Array.set(array, index, decode(type.element(), items.get(index)));
        }
        return array;
    }

    private static Object decodeList(DslType.ListOf type, JsonElement json) {
        List<Object> list = new ArrayList<>();
        for (JsonElement item : Json.asArray(json, type.toString())) {
            list.add(decode(type.element(), item));
        }
        return list;
    }

    private static Object decodeNode(DslType.Node type, JsonElement json) {
        return switch (type.kind()) {
            case LIST_NODE -> Nodes.decodeList(json);
            case TREE_NODE -> Nodes.decodeTree(json);
            case GRAPH_NODE -> Nodes.decodeGraph(json);
        };
    }

    private static <T> T exact(JsonElement json, String typeName, Function<BigDecimal, T> convert) {
        try {
            return convert.apply(number(json, typeName).getAsBigDecimal());
        } catch (ArithmeticException error) {
            throw new BadRequestException(json + " is not a valid " + typeName);
        }
    }

    private static JsonElement number(JsonElement json, String typeName) {
        if (!Json.isNumber(json)) {
            throw new BadRequestException(json + " is not a valid " + typeName);
        }
        return json;
    }

    private static String string(DslType type, JsonElement json) {
        if (!Json.isString(json)) {
            throw malformed(type, json);
        }
        return json.getAsString();
    }

    private static BadRequestException malformed(DslType type, JsonElement json) {
        return new BadRequestException(json + " is not a valid " + type);
    }

    private static JsonElement encodeScalar(DslType.Scalar type, Object value)
            throws InvalidOutputException {
        JsonPrimitive encoded = switch (type.kind()) {
            case INT -> value instanceof Integer number ? new JsonPrimitive(number) : null;
            case LONG -> value instanceof Long number ? new JsonPrimitive(number) : null;
            case DOUBLE -> value instanceof Double number ? finite(number) : null;
            case BOOL -> value instanceof Boolean flag ? new JsonPrimitive(flag) : null;
            case STRING -> value instanceof String text ? new JsonPrimitive(text) : null;
            case CHAR -> value instanceof Character character ? new JsonPrimitive(character) : null;
            case DECIMAL -> value instanceof BigDecimal number ? canonical(number) : null;
            case DATE -> value instanceof LocalDate day ? calendarDay(day) : null;
        };
        if (encoded == null) {
            throw mismatch(type, value);
        }
        return encoded;
    }

    private static JsonPrimitive canonical(BigDecimal number) {
        if (number.signum() == 0) {
            return new JsonPrimitive("0");
        }
        return new JsonPrimitive(number.stripTrailingZeros().toPlainString());
    }

    private static JsonPrimitive calendarDay(LocalDate day) throws InvalidOutputException {
        if (day.getYear() < 1 || day.getYear() > 9999) {
            throw new InvalidOutputException("date " + day + " is outside years 0001 to 9999");
        }
        return new JsonPrimitive(day.toString());
    }

    private static JsonPrimitive finite(double number) throws InvalidOutputException {
        if (!Double.isFinite(number)) {
            throw new InvalidOutputException("non-finite double " + number);
        }
        return new JsonPrimitive(number);
    }

    private static JsonElement encodeArray(DslType.ArrayOf type, Object value)
            throws InvalidOutputException {
        if (value == null || !value.getClass().isArray()) {
            throw mismatch(type, value);
        }
        JsonArray encoded = new JsonArray();
        for (int index = 0; index < Array.getLength(value); index++) {
            encoded.add(encode(type.element(), Array.get(value, index)));
        }
        return encoded;
    }

    private static JsonElement encodeList(DslType.ListOf type, Object value)
            throws InvalidOutputException {
        if (!(value instanceof List<?> list)) {
            throw mismatch(type, value);
        }
        JsonArray encoded = new JsonArray();
        for (Object item : list) {
            encoded.add(encode(type.element(), item));
        }
        return encoded;
    }

    private static JsonElement encodeNode(DslType.Node type, Object value)
            throws InvalidOutputException {
        if (value != null && !type.jvmClass().isInstance(value)) {
            throw mismatch(type, value);
        }
        return switch (type.kind()) {
            case LIST_NODE -> Nodes.encodeList((ListNode) value);
            case TREE_NODE -> Nodes.encodeTree((TreeNode) value);
            case GRAPH_NODE -> Nodes.encodeGraph((GraphNode) value);
        };
    }

    private static InvalidOutputException mismatch(DslType type, Object value) {
        String actual = value == null ? "null" : value.getClass().getName();
        return new InvalidOutputException("expected " + type + ", got " + actual);
    }
}
