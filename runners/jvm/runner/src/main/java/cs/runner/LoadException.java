package cs.runner;

/** The target class, constructor or method cannot be loaded (event load_error). */
final class LoadException extends Exception {
    private final UserError error;

    LoadException(String type, String message) {
        this(new UserError(type, message, ""));
    }

    LoadException(UserError error) {
        super(error.message(), null, false, false);
        this.error = error;
    }

    UserError error() {
        return error;
    }
}
