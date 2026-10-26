package cs.runner;

import com.google.gson.JsonObject;
import java.nio.file.Path;

/** The request file (docs/specs/runners.md#request-file): a {@code test} or {@code bench} run. */
sealed interface RunnerRequest permits Request, BenchRequest {
    String TEST_MODE = "test";
    String BENCH_MODE = "bench";

    static RunnerRequest read(Path path) {
        JsonObject document = Json.asObject(Request.parse(path), "request");
        int protocol = Json.integer(document, "protocol");
        if (protocol != Request.PROTOCOL) {
            throw new BadRequestException("unknown protocol " + protocol);
        }
        String mode = Json.string(document, "mode");
        return switch (mode) {
            case TEST_MODE -> Request.of(document);
            case BENCH_MODE -> BenchRequest.of(document);
            default -> throw new BadRequestException("unsupported mode \"" + mode + "\"");
        };
    }
}
