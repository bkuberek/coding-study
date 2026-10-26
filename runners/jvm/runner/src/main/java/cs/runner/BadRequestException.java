package cs.runner;

/** The request is unusable (exit code 2): malformed JSON, an unknown type, or an invalid input. */
final class BadRequestException extends RuntimeException {
    BadRequestException(String message) {
        super(message);
    }
}
