package coworking.vendors;

/** A vendor gave no usable answer: every way a vendor can fail ends as this. */
public final class VendorUnavailableException extends Exception {
    public VendorUnavailableException(String message) {
        super(message);
    }

    public VendorUnavailableException(String message, Throwable cause) {
        super(message, cause);
    }
}
