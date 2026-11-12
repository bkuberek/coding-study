import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.EmptyStackException;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.Stack;

// The legacy Stack class and an ArrayDeque used as a stack agree on push, pop and peek, but not on
// the order in which they list their elements, nor on what happens when they are empty.
public class StackOrder {
    public static void main(String[] args) {
        Stack<String> legacy = new Stack<>();
        Deque<String> deque = new ArrayDeque<>();
        for (String item : List.of("a", "b", "c")) {
            legacy.push(item);
            deque.push(item);
        }
        System.out.println("peek:  Stack " + legacy.peek() + ", ArrayDeque " + deque.peek());
        System.out.println("list:  Stack " + new ArrayList<>(legacy) + ", ArrayDeque " + new ArrayList<>(deque));
        legacy.add(0, "z");  // Stack extends Vector, so any index is open to change
        System.out.println("Stack after add(0, \"z\"): " + legacy);

        Deque<String> empty = new ArrayDeque<>();
        System.out.println("empty ArrayDeque, peek(): " + empty.peek());
        try {
            empty.pop();
        } catch (NoSuchElementException error) {
            System.out.println("empty ArrayDeque, pop(): NoSuchElementException");
        }
        try {
            new Stack<String>().pop();
        } catch (EmptyStackException error) {
            System.out.println("empty Stack, pop(): EmptyStackException");
        }
        try {
            deque.push(null);
        } catch (NullPointerException error) {
            System.out.println("ArrayDeque, push(null): NullPointerException");
        }
    }
}
