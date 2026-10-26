package cs.runner;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonPrimitive;

/** Typed access to request fields; every failure is a bad request. */
final class Json {
    private Json() {
    }

    static JsonElement field(JsonObject object, String key) {
        JsonElement value = object.get(key);
        if (value == null) {
            throw new BadRequestException("missing \"" + key + "\"");
        }
        return value;
    }

    static JsonObject object(JsonObject object, String key) {
        return asObject(field(object, key), key);
    }

    static JsonArray array(JsonObject object, String key) {
        return asArray(field(object, key), key);
    }

    static String string(JsonObject object, String key) {
        JsonElement value = field(object, key);
        if (!isString(value)) {
            throw new BadRequestException("\"" + key + "\" must be a string");
        }
        return value.getAsString();
    }

    static String optionalString(JsonObject object, String key) {
        return object.has(key) ? string(object, key) : null;
    }

    static int integer(JsonObject object, String key) {
        JsonElement value = field(object, key);
        if (!isNumber(value)) {
            throw new BadRequestException("\"" + key + "\" must be an integer");
        }
        return value.getAsInt();
    }

    static JsonObject asObject(JsonElement value, String what) {
        if (!value.isJsonObject()) {
            throw new BadRequestException("\"" + what + "\" must be an object");
        }
        return value.getAsJsonObject();
    }

    static JsonArray asArray(JsonElement value, String what) {
        if (!value.isJsonArray()) {
            throw new BadRequestException("\"" + what + "\" must be an array");
        }
        return value.getAsJsonArray();
    }

    static boolean isString(JsonElement value) {
        return value instanceof JsonPrimitive primitive && primitive.isString();
    }

    static boolean isNumber(JsonElement value) {
        return value instanceof JsonPrimitive primitive && primitive.isNumber();
    }

    static boolean isBoolean(JsonElement value) {
        return value instanceof JsonPrimitive primitive && primitive.isBoolean();
    }
}
