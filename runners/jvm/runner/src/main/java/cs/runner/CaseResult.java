package cs.runner;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

/**
 * The outcome of one case: {@code case_result} statuses ok, error and invalid_output, and for
 * stress runs also stalled (docs/specs/runners.md#events).
 */
sealed interface CaseResult {
    long durationNs();

    /** Adds {@code status} and the status-specific fields to a case_result event. */
    void describe(JsonObject event);

    record Returned(JsonElement output, long durationNs) implements CaseResult {
        @Override
        public void describe(JsonObject event) {
            event.addProperty("status", "ok");
            event.add("output", output);
        }
    }

    /** {@code opIndex} and {@code partialOutput} are null for function kinds. */
    record Raised(UserError error, long durationNs, Integer opIndex, JsonArray partialOutput)
            implements CaseResult {
        static Raised fromFunction(UserError error, long durationNs) {
            return new Raised(error, durationNs, null, null);
        }

        @Override
        public void describe(JsonObject event) {
            event.addProperty("status", "error");
            event.add("error", error.toJson());
            if (opIndex != null) {
                event.addProperty("op_index", opIndex);
                event.add("partial_output", partialOutput);
            }
        }
    }

    record InvalidOutput(String reason, long durationNs) implements CaseResult {
        @Override
        public void describe(JsonObject event) {
            event.addProperty("status", "invalid_output");
            event.addProperty("reason", reason);
        }
    }

    /** A stress run in which every worker finished and the final script ran. */
    record StressReturned(JsonObject output, JsonObject sections, long durationNs)
            implements CaseResult {
        @Override
        public void describe(JsonObject event) {
            event.addProperty("status", "ok");
            event.add("output", output);
            event.add("sections", sections);
        }
    }

    /**
     * A stress run that failed with {@code failure} (an error or invalid output) in a phase.
     *
     * @param worker the failing worker's ordinal, null for the setup and final phases
     * @param progress the unfinished workers, null for the setup and final phases
     */
    record StressFailed(
            CaseResult failure, String phase, int opIndex, Integer worker, JsonArray progress)
            implements CaseResult {
        @Override
        public long durationNs() {
            return failure.durationNs();
        }

        @Override
        public void describe(JsonObject event) {
            failure.describe(event);
            event.addProperty("phase", phase);
            event.addProperty("op_index", opIndex);
            if (worker != null) {
                event.addProperty("worker", worker);
                event.add("progress", progress);
            }
        }
    }

    /** Workers were still unfinished at the run's deadline. */
    record Stalled(JsonArray progress, long durationNs) implements CaseResult {
        @Override
        public void describe(JsonObject event) {
            event.addProperty("status", "stalled");
            event.add("progress", progress);
        }
    }
}
