package cs.runner;

/** A return value that cannot be serialized as its declared type (status invalid_output). */
final class InvalidOutputException extends Exception {
    InvalidOutputException(String reason) {
        super(reason, null, false, false);
    }
}
