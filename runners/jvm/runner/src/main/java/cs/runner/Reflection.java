package cs.runner;

import java.lang.reflect.Constructor;
import java.lang.reflect.Executable;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Finds and calls user code (docs/specs/runners.md#locating-user-code).
 *
 * <p>Kotlin types compile to the same JVM types as the Java column of the mapping table, so one
 * lookup serves both languages. A parameter matches when it can receive the value the runner
 * decodes: primitives exactly, everything else by assignability.
 */
final class Reflection {
    private static final String NO_SUCH_METHOD = "NoSuchMethodException";
    private static final String CLASS_NOT_FOUND = "ClassNotFoundException";

    private Reflection() {
    }

    /** A call's result and how long only the call took. */
    record Timed(Object value, long durationNs) {
    }

    /** User code threw; {@code getCause()} is the user's exception. */
    static final class UserCodeException extends Exception {
        private final long durationNs;

        UserCodeException(Throwable cause, long durationNs) {
            super(cause);
            this.durationNs = durationNs;
        }

        long durationNs() {
            return durationNs;
        }
    }

    static Class<?> loadClass(String className) throws LoadException {
        try {
            return Class.forName(className, true, Reflection.class.getClassLoader());
        } catch (ClassNotFoundException error) {
            throw new LoadException(CLASS_NOT_FOUND, "class " + className + " not found");
        } catch (ExceptionInInitializerError error) {
            Throwable cause = error.getCause() == null ? error : error.getCause();
            throw new LoadException(UserError.of(cause, packageOf(className)));
        } catch (LinkageError error) {
            String type = UserError.typeName(error.getClass());
            throw new LoadException(type, String.valueOf(error.getMessage()));
        }
    }

    static Method method(Class<?> type, Member member) throws LoadException {
        for (Class<?> owner = type;
                owner != null && owner != Object.class;
                owner = owner.getSuperclass()) {
            for (Method method : owner.getDeclaredMethods()) {
                boolean candidate = !method.isSynthetic() && method.getName().equals(member.name());
                if (candidate && accepts(method, member.params())) {
                    method.setAccessible(true);
                    return method;
                }
            }
        }
        String expected = member.name() + describe(member.params());
        throw new LoadException(NO_SUCH_METHOD, "no method " + expected + " in " + type.getName());
    }

    static Constructor<?> constructor(Class<?> type, List<Member.Param> params)
            throws LoadException {
        for (Constructor<?> constructor : type.getDeclaredConstructors()) {
            if (accepts(constructor, params)) {
                constructor.setAccessible(true);
                return constructor;
            }
        }
        String expected = type.getSimpleName() + describe(params);
        String message = "no constructor " + expected + " in " + type.getName();
        throw new LoadException(NO_SUCH_METHOD, message);
    }

    static Timed invoke(Method method, Object instance, Object[] arguments)
            throws UserCodeException {
        long start = System.nanoTime();
        try {
            Object value = method.invoke(instance, arguments);
            return new Timed(value, System.nanoTime() - start);
        } catch (InvocationTargetException error) {
            throw new UserCodeException(error.getCause(), System.nanoTime() - start);
        } catch (IllegalAccessException error) {
            throw new IllegalStateException(error);
        }
    }

    static Timed construct(Constructor<?> constructor, Object[] arguments)
            throws UserCodeException {
        long start = System.nanoTime();
        try {
            Object value = constructor.newInstance(arguments);
            return new Timed(value, System.nanoTime() - start);
        } catch (InvocationTargetException error) {
            throw new UserCodeException(error.getCause(), System.nanoTime() - start);
        } catch (IllegalAccessException | InstantiationException error) {
            throw new IllegalStateException(error);
        }
    }

    /** Calls user code without timing it (bench mode times many calls at once). */
    static Object call(Method method, Object instance, Object[] arguments)
            throws UserCodeException {
        try {
            return method.invoke(instance, arguments);
        } catch (InvocationTargetException error) {
            throw new UserCodeException(error.getCause(), 0);
        } catch (IllegalAccessException error) {
            throw new IllegalStateException(error);
        }
    }

    static Object create(Constructor<?> constructor, Object[] arguments)
            throws UserCodeException {
        try {
            return constructor.newInstance(arguments);
        } catch (InvocationTargetException error) {
            throw new UserCodeException(error.getCause(), 0);
        } catch (IllegalAccessException | InstantiationException error) {
            throw new IllegalStateException(error);
        }
    }

    static String packageOf(String className) {
        int lastDot = className.lastIndexOf('.');
        return lastDot < 0 ? "" : className.substring(0, lastDot);
    }

    private static boolean accepts(Executable executable, List<Member.Param> params) {
        Class<?>[] parameterTypes = executable.getParameterTypes();
        if (parameterTypes.length != params.size()) {
            return false;
        }
        for (int index = 0; index < parameterTypes.length; index++) {
            if (!accepts(parameterTypes[index], params.get(index).type())) {
                return false;
            }
        }
        return true;
    }

    private static boolean accepts(Class<?> parameter, DslType type) {
        Class<?> decoded = type instanceof DslType.ListOf ? ArrayList.class : type.jvmClass();
        return decoded.isPrimitive() ? parameter == decoded : parameter.isAssignableFrom(decoded);
    }

    private static String describe(List<Member.Param> params) {
        return params.stream()
                .map(param -> param.type().jvmClass().getSimpleName())
                .collect(Collectors.joining(", ", "(", ")"));
    }
}
