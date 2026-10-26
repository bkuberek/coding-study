package cs.runner;

import com.google.gson.JsonArray;
import com.google.gson.JsonNull;
import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * A design, progressive or concurrent job: {@code ops[0]} constructs the class, every later op
 * calls a method; outputs are collected per op (docs/specs/problem-format.md#operation-sequences).
 */
final class ClassTarget implements Target<Request.OperationsCase> {
    private static final int CONSTRUCTOR_OP = 0;

    private record BoundMethod(Member member, Method method) {
    }

    private final Member constructorMember;
    private final Constructor<?> constructor;
    private final Map<String, BoundMethod> methods;
    private final String userPackage;

    private ClassTarget(
            Member constructorMember,
            Constructor<?> constructor,
            Map<String, BoundMethod> methods,
            String userPackage) {
        this.constructorMember = constructorMember;
        this.constructor = constructor;
        this.methods = methods;
        this.userPackage = userPackage;
    }

    static ClassTarget load(Request.ClassJob job) throws LoadException {
        Class<?> type = Reflection.loadClass(job.className());
        Constructor<?> constructor = Reflection.constructor(type, job.constructor().params());
        Map<String, BoundMethod> methods = new LinkedHashMap<>();
        for (Map.Entry<String, Member> entry : job.methods().entrySet()) {
            Member member = entry.getValue();
            methods.put(entry.getKey(), new BoundMethod(member, Reflection.method(type, member)));
        }
        String userPackage = Reflection.packageOf(job.className());
        return new ClassTarget(job.constructor(), constructor, methods, userPackage);
    }

    @Override
    public PreparedCase prepare(Request.OperationsCase testCase) {
        List<String> ops = testCase.ops();
        List<BoundMethod> calls = new ArrayList<>();
        List<Object[]> arguments = new ArrayList<>();
        decode(testCase, calls, arguments);
        return () -> run(ops, calls, arguments);
    }

    /** The whole sequence as one call: construct, then call each method on the instance. */
    @Override
    public RawCall prepareCall(Request.OperationsCase testCase) {
        List<BoundMethod> calls = new ArrayList<>();
        List<Object[]> arguments = new ArrayList<>();
        decode(testCase, calls, arguments);
        return () -> {
            Object instance = Reflection.create(constructor, arguments.get(CONSTRUCTOR_OP));
            Object[] results = new Object[calls.size()];
            results[CONSTRUCTOR_OP] = instance;
            for (int op = CONSTRUCTOR_OP + 1; op < calls.size(); op++) {
                results[op] = Reflection.call(calls.get(op).method(), instance, arguments.get(op));
            }
            return results;
        };
    }

    @Override
    public String userPackage() {
        return userPackage;
    }

    /** One decoded op of a stress script: the method and fresh arguments for one call. */
    record PreparedOp(Member member, Method method, Object[] arguments) {
    }

    /** Decodes the arguments of one call of {@code op}; a malformed input is a bad request. */
    PreparedOp prepareOp(String op, JsonArray args) {
        BoundMethod bound = method(op);
        Object[] arguments = Arguments.decode(bound.member(), args.asList());
        return new PreparedOp(bound.member(), bound.method(), arguments);
    }

    Object construct(JsonArray args) throws Reflection.UserCodeException {
        return Reflection.create(constructor, Arguments.decode(constructorMember, args.asList()));
    }

    /** Calls a prepared op on {@code instance} and serializes its result. */
    static com.google.gson.JsonElement call(PreparedOp op, Object instance)
            throws Reflection.UserCodeException, InvalidOutputException {
        Outputs.Snapshot snapshot = Outputs.beforeCall(op.member(), op.arguments());
        Object value = Reflection.call(op.method(), instance, op.arguments());
        return Outputs.serialize(op.member(), op.arguments(), value, snapshot);
    }

    private void decode(
            Request.OperationsCase testCase, List<BoundMethod> calls, List<Object[]> arguments) {
        List<String> ops = testCase.ops();
        for (int op = 0; op < ops.size(); op++) {
            BoundMethod call = op == CONSTRUCTOR_OP ? null : method(ops.get(op));
            Member member = call == null ? constructorMember : call.member();
            calls.add(call);
            arguments.add(Arguments.decode(member, testCase.args().get(op).asList()));
        }
    }

    private BoundMethod method(String op) {
        BoundMethod method = methods.get(op);
        if (method == null) {
            throw new BadRequestException("unknown operation \"" + op + "\"");
        }
        return method;
    }

    private CaseResult run(List<String> ops, List<BoundMethod> calls, List<Object[]> arguments) {
        JsonArray outputs = new JsonArray();
        long durationNs = 0;
        Object instance = null;
        for (int op = 0; op < ops.size(); op++) {
            try {
                if (op == CONSTRUCTOR_OP) {
                    Reflection.Timed created = Reflection.construct(constructor, arguments.get(op));
                    instance = created.value();
                    durationNs += created.durationNs();
                    outputs.add(JsonNull.INSTANCE);
                    continue;
                }
                Member member = calls.get(op).member();
                Object[] opArguments = arguments.get(op);
                Outputs.Snapshot snapshot = Outputs.beforeCall(member, opArguments);
                Method method = calls.get(op).method();
                Reflection.Timed call = Reflection.invoke(method, instance, opArguments);
                durationNs += call.durationNs();
                outputs.add(Outputs.serialize(member, opArguments, call.value(), snapshot));
            } catch (Reflection.UserCodeException error) {
                UserError raised = UserError.of(error.getCause(), userPackage);
                return new CaseResult.Raised(raised, durationNs + error.durationNs(), op, outputs);
            } catch (InvalidOutputException error) {
                String reason = "op " + op + " (" + ops.get(op) + "): " + error.getMessage();
                return new CaseResult.InvalidOutput(reason, durationNs);
            }
        }
        return new CaseResult.Returned(outputs, durationNs);
    }
}
