package cs.runner;

import com.google.gson.JsonObject;
import java.util.ArrayList;
import java.util.List;

/** An exception from user code, or why a target could not be loaded. */
record UserError(String type, String message, String trace) {
    static final int MAX_TRACE_LINES = 10;

    /** Describes {@code error}, keeping only stack frames from classes in {@code userPackage}. */
    static UserError of(Throwable error, String userPackage) {
        String message = error.getMessage() == null ? "" : error.getMessage();
        return new UserError(typeName(error.getClass()), message, trace(error, userPackage));
    }

    static String typeName(Class<?> type) {
        String simpleName = type.getSimpleName();
        return simpleName.isEmpty() ? type.getName() : simpleName;
    }

    JsonObject toJson() {
        JsonObject encoded = new JsonObject();
        encoded.addProperty("type", type);
        encoded.addProperty("message", message);
        if (!trace.isEmpty()) {
            encoded.addProperty("trace", trace);
        }
        return encoded;
    }

    private static String trace(Throwable error, String userPackage) {
        String prefix = userPackage + ".";
        List<String> lines = new ArrayList<>();
        for (StackTraceElement frame : error.getStackTrace()) {
            if (frame.getClassName().startsWith(prefix) && lines.size() < MAX_TRACE_LINES) {
                lines.add(frame(frame));
            }
        }
        return String.join("\n", lines);
    }

    private static String frame(StackTraceElement frame) {
        String className = frame.getClassName();
        String simpleClass = className.substring(className.lastIndexOf('.') + 1);
        return frame.getFileName() + ":" + frame.getLineNumber()
                + " in " + simpleClass + "." + frame.getMethodName();
    }
}
