package cs.runner;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import java.util.ArrayList;
import java.util.List;

/**
 * A function, constructor or method from the request signature, with modifiers.
 *
 * @param name the JVM name to look up (from the request's {@code names})
 * @param async a Kotlin {@code suspend} method ({@code "async": true}), whose JVM signature takes
 *     a continuation after the declared parameters
 */
record Member(String name, List<Param> params, Returns returns, boolean async) {
    static final String VOID = "void";
    private static final String ASYNC = "async";

    record Param(String name, DslType type, String refOf) {
    }

    /** {@code type} is null for void. */
    record Returns(
            DslType type,
            String outputFrom,
            String serializeAs,
            String indexOf,
            String noAliasWith) {
        static final String AS_VALUE = "value";
        static final String AS_INDEX = "index";
        static final Returns NOTHING = new Returns(null, null, null, null, null);

        boolean isVoid() {
            return type == null;
        }
    }

    static Member parse(String name, JsonObject signature) {
        List<Param> params = parseParams(Json.array(signature, "params"));
        return new Member(name, params, parseReturns(signature), parseAsync(signature));
    }

    static Member constructor(String name, JsonObject signature) {
        List<Param> params = parseParams(Json.array(signature, "params"));
        return new Member(name, params, Returns.NOTHING, false);
    }

    Param param(String paramName) {
        for (Param param : params) {
            if (param.name().equals(paramName)) {
                return param;
            }
        }
        throw new BadRequestException("no parameter \"" + paramName + "\" in " + name);
    }

    private static boolean parseAsync(JsonObject signature) {
        if (!signature.has(ASYNC)) {
            return false;
        }
        JsonElement async = signature.get(ASYNC);
        if (!Json.isBoolean(async)) {
            throw new BadRequestException("\"" + ASYNC + "\" must be a boolean");
        }
        return async.getAsBoolean();
    }

    private static List<Param> parseParams(JsonArray encoded) {
        List<Param> params = new ArrayList<>();
        for (JsonElement element : encoded) {
            JsonObject param = Json.asObject(element, "params");
            params.add(new Param(
                    Json.string(param, "name"),
                    DslType.parse(Json.string(param, "type")),
                    Json.optionalString(param, "ref_of")));
        }
        return List.copyOf(params);
    }

    private static Returns parseReturns(JsonObject signature) {
        JsonObject returns = Json.object(signature, "returns");
        String type = Json.string(returns, "type");
        return new Returns(
                VOID.equals(type) ? null : DslType.parse(type),
                Json.optionalString(returns, "output_from"),
                Json.optionalString(returns, "as"),
                Json.optionalString(returns, "of"),
                Json.optionalString(returns, "no_alias_with"));
    }
}
