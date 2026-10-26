package cs.runner;

import com.google.gson.JsonElement;
import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.List;

/** A function-kind job: a method of {@code Solution}, called on a fresh instance per case. */
final class FunctionTarget implements Target<Request.FunctionCase> {
    private static final Object[] NO_ARGUMENTS = {};

    private final Member function;
    private final Method method;
    private final Constructor<?> constructor;
    private final String userPackage;

    private FunctionTarget(
            Member function, Method method, Constructor<?> constructor, String userPackage) {
        this.function = function;
        this.method = method;
        this.constructor = constructor;
        this.userPackage = userPackage;
    }

    static FunctionTarget load(Request.FunctionJob job) throws LoadException {
        Class<?> type = Reflection.loadClass(job.className());
        Method method = Reflection.method(type, job.function());
        Constructor<?> constructor = Modifier.isStatic(method.getModifiers())
                ? null
                : Reflection.constructor(type, List.of());
        String userPackage = Reflection.packageOf(job.className());
        return new FunctionTarget(job.function(), method, constructor, userPackage);
    }

    @Override
    public PreparedCase prepare(Request.FunctionCase testCase) {
        Object[] arguments = arguments(testCase);
        return () -> run(arguments);
    }

    /** The instance is created here, outside the timed call, like a fresh one per case. */
    @Override
    public RawCall prepareCall(Request.FunctionCase testCase) throws Reflection.UserCodeException {
        Object[] arguments = arguments(testCase);
        Object instance = constructor == null ? null : Reflection.create(constructor, NO_ARGUMENTS);
        return () -> Reflection.call(method, instance, arguments);
    }

    @Override
    public String userPackage() {
        return userPackage;
    }

    private Object[] arguments(Request.FunctionCase testCase) {
        List<JsonElement> values = function.params().stream()
                .map(param -> Json.field(testCase.input(), param.name()))
                .toList();
        return Arguments.decode(function, values);
    }

    private CaseResult run(Object[] arguments) {
        Outputs.Snapshot snapshot = Outputs.beforeCall(function, arguments);
        Reflection.Timed call;
        try {
            Object instance = constructor == null
                    ? null
                    : Reflection.construct(constructor, NO_ARGUMENTS).value();
            call = Reflection.invoke(method, instance, arguments);
        } catch (Reflection.UserCodeException error) {
            UserError raised = UserError.of(error.getCause(), userPackage);
            return CaseResult.Raised.fromFunction(raised, error.durationNs());
        }
        try {
            JsonElement output = Outputs.serialize(function, arguments, call.value(), snapshot);
            return new CaseResult.Returned(output, call.durationNs());
        } catch (InvalidOutputException error) {
            return new CaseResult.InvalidOutput(error.getMessage(), call.durationNs());
        }
    }
}
