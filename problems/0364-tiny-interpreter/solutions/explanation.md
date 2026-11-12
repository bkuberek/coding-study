# Tiny Interpreter: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| pratt-and-stack-vm | optimal | O(s) per tokenize, parse or compile; O(s + w * h) per evaluate or run | O(s + w) | default answer: a Pratt parser shared by a tree walker and a bytecode compiler |

`s` is the length of the source, `w` the number of steps the program takes when it runs (nodes evaluated or instructions executed), and `h` the number of scopes a name lookup may walk through.

## How the design grows level by level

| Level | What changes | Design move |
|-------|--------------|-------------|
| 1 | Text becomes tokens | A loop over the source with a line and column counter; each character decides which kind of token starts there, and the longest symbol wins |
| 2 | Tokens become a tree | A Pratt parser: one function parses an expression, and a table of binding powers decides how far each operator reaches. `let`, `if` and `fn` are prefix forms whose last part is a full expression |
| 3 | The tree gets a value | A recursive walk with a chain of scopes. A function value is a closure: its parameters, its body and the scope it was created in |
| 4 | The tree becomes instructions | A compiler emits one block per function into lists of instructions, and a loop runs them with an explicit stack of frames. The operators, the call checks and the scopes are the ones of level 3, so both paths fail the same way |

Each level reuses the previous one: `parse` tokenizes, `evaluate` and `bytecode` parse, and `run` compiles.

## Approach: pratt-and-stack-vm (A Pratt parser with a tree walker and a bytecode stack machine)

### Intuition

**Parsing by binding power.** Writing a function per precedence level works, but adding a level means adding a function. Top-down operator precedence, Pratt's 1973 technique, gives each operator a number instead. `expression(minimum)` parses one operand, then keeps absorbing operators whose power is greater than `minimum`: when it meets `*` (power 3) inside the right side of `+` (power 2), the inner call takes it, so `1 + 2 * 3` nests the product. Left grouping falls out of passing an operator's own power for its right side, since an equal operator then stops the inner call; right grouping, for `^`, passes one less, so another `^` still binds inside. Prefix minus parses its operand at power 4, between `*` and `^`, which is exactly "`-2 ^ 2` is `-(2 ^ 2)` and `-x * y` is `(-x) * y`". Calls are an operator of power 6 that happens to be followed by an argument list.

**Closures by scope chains.** A scope is a small map plus a pointer to the enclosing scope. A `let` or a call creates a new map in front of an existing chain and never changes the old one. A function value keeps the chain where it was created, so its free names are looked up there (lexical scope) however long after the call that created them returned.

**A machine without recursion.** The tree walker uses the host language's own call stack: a program that recurses 100 deep makes the walker recurse several hundred deep. The bytecode machine keeps its frames in a list and loops, so its depth is data. Compiling first also turns the work of deciding what to do next (which kind of node is this?) into a flat sequence decided once.

### Algorithm

1. **Tokens.** Walk the source with an index, a line and a column. Skip spaces, tabs and comments; a newline moves to the next line. Read a maximal run of digits (rejecting a leading `0` and values above 2147483647), a maximal name (a keyword when it is one of the six), a two-character symbol when the next two characters form one, else a one-character symbol, else fail with `bad-char`. Add `end` at the final position.
2. **Tree.** `expression(minimum)` calls `prefix()`: a number, a name, `-` (operand at power 4), `(` (an inner expression and `)`), `let`, `if` or `fn`, whose parts are full expressions at power 0. Then, while the next token is `(` and 6 is above `minimum`, parse a call; or while it is a binary operator whose power is above `minimum`, take it and parse the right side at its power, minus one for `^`. Anything else ends the loop. The program is one expression followed by `end`; an unexpected token fails where it is met. Number each `fn` as it is met.
3. **Evaluation.** Recurse over the tree with the current scope and the number of calls in progress. Operators compute both operands, then check types, zero divisors and negative exponents, then compute in 64 bits and check the 32-bit range. `/` truncates and `%` takes the sign of the left operand. A call computes the callee and the arguments, checks callable, arity and depth in that order at the `(`, then evaluates the body in a new scope over the closure's scope, holding the function's own name and then the parameters, with one more call in progress.
4. **Bytecode.** Walk the tree once per block, appending instructions as the statement's table says. For `if`, append `JUMP_IF_ZERO` and `JUMP` with empty targets and fill them in when the targets are known (back-patching). A `fn` creates its block, compiles its body into it, and appends `CLOSURE k` to the current block.
5. **Machine.** Keep one value stack and a list of frames (block, instruction index, scope), starting with block 0 and an empty scope. Loop: fetch the instruction at the top frame's index, advance the index, act. `CALL` pops the arguments and the callee, runs the level 3 checks with the frames above the program's as the calls in progress, and pushes a frame; `RETURN` pops the frame and leaves the value for the caller, or ends the run at the program's frame.

### Correctness

**Tokens.** Each kind of token starts with a different class of character, so the first character decides the kind, and taking the longest match is what the statement asks for symbols, numbers and names.

**Parsing.** By induction on the expression: `expression(m)` returns the longest expression starting at the current token whose operators all bind tighter than `m`. An operator of power `p` absorbs into the left side exactly when `p > m`; its right side is parsed with minimum `p` (left grouping) or `p - 1` (right grouping), which stops at the first operator that binds no tighter, which is the grouping rule. `let`, `if` and `fn` parse their last part at minimum 0, so it extends as far right as any expression can. The parser consumes tokens left to right and never backtracks, and fails at the first token that no rule can take, which is the first token at which no valid program continues.

**Evaluation.** Every rule of the statement is one branch: the order of computation is the order of the recursive calls, and each check sits where the statement puts it. Lexical scope holds because a closure's body runs in a scope built over the chain stored at its creation, never over the caller's chain.

**Bytecode.** By induction on the tree, the instructions of a node leave exactly one value on the stack (its value), with every `BIND` matched by an `UNBIND`, and they compute the same values in the same order as the walker does: operands before operators, the callee and the arguments before the call checks, the condition before the jump that skips the other branch. Both paths share the operator, condition and call-check functions, so every failure has the same code and position. The frames above the program's are exactly the calls in progress, so the depth check matches too.

### Complexity

- Time: O(s) per tokenize, parse or compile; O(s + w * h) per evaluate or run — the tokenizer, the parser and the compiler each handle every character, token or node a constant number of times; running takes `w` steps, and a name lookup walks up to `h` scopes.
- Space: O(s + w) — the tokens, tree and bytecode are linear in the source; scopes created while running can stay alive inside closures, at most one per step.

### Trade-offs

- **Resolved variables.** Looking names up by text, scope after scope, keeps the compiler simple and the listing readable. Real compilers resolve each name at compile time to a slot in the current frame or a captured variable, so a load is one array access; the price is a resolver pass and a representation for captured variables that outlive their frame.
- **Tree walker or bytecode.** The walker is shorter and easier to debug; it is enough for configuration languages and templates. Bytecode pays off when programs run long or recurse deep: dispatch over a flat array is cheaper than chasing tree pointers, and the explicit frames make depth a matter of memory.
- **Recursive descent with one function per level.** Equivalent for this grammar and easy to read, but every new precedence level is a new function and an operator's grouping is spread over the code. A table of binding powers keeps precedence and associativity in one place.
- **Exceptions or results.** Errors here stop the whole run, so Python, TypeScript, Java and Kotlin throw an error object that the public methods catch, Go panics with a typed value recovered at the API boundary, and Rust returns `Result` with `?`.

### Pitfalls and edge cases

- Symbols: `>=` read as `>` then `=` breaks comparisons and `=>`; `==>` is `==` then `>`.
- Positions: columns from 1, a tab is one column, the `end` token after a final newline is on the next line.
- Numbers: `007` and `2147483648` are errors, `0` is not; `-2147483648` cannot be written directly, only as `-2147483647 - 1`.
- Precedence: `-2 ^ 2` is -4, `2 ^ 3 ^ 2` is 512, `10 - 4 - 3` is 3, and `1 + let x = 2 in x * 3` keeps the multiplication inside the `let`.
- Division: `/` truncates towards zero and `%` keeps the sign of the left operand, unlike Python's `//` and `%`; `-2147483648 / -1` overflows while `-2147483648 % -1` is 0.
- Order of checks: operands are computed before the type check, so `(fn () => 1) + y` is `unbound`, not `type`; arguments are computed before the callable and arity checks; arity is checked before depth.
- Scope: a `let` value sees the outer name, a function's own name is visible only inside its body, and a parameter with the same name hides the function.
- Depth: `maxDepth` calls may be in progress; the next one fails. Counting the program's frame in the machine makes `run` fail one call early.
- Bytecode: blocks are numbered by the position of their `fn` keyword, which is the order a compiler meets them when it numbers a function before compiling its body; jump targets are absolute indexes in the block.

### Language notes

- Python and TypeScript integers: Python's are unbounded, so every result is checked against the 32-bit range. TypeScript's `number` is a double: a sum or difference of two 32-bit values is exact, and a product too large to be exact is far outside the range, where rounding cannot bring it back inside, so the overflow check still decides correctly; `Math.trunc` gives truncating division.
- Java and Kotlin compute in `long` and narrow to `int` after the check; Go in `int64`; Rust in `i64`.
- The tree is a sealed interface of records in Java, a sealed class in Kotlin, a tagged union type in TypeScript, an `enum` in Rust and an interface with one struct per node in Go.
- Rust shares scopes and closures with `Rc`; a function value holds an `Rc` of its tree node for the walker, or only its block number for the machine.
- The machine never recurses, but the tree walker and the parser do: the runners give Python, Java, Kotlin and Rust large thread stacks, Go's stacks grow on demand, and TypeScript's default stack holds the 100-deep recursion and 50-deep nesting the constraints allow.

## Further reading

- V. R. Pratt, *Top down operator precedence*, Proceedings of the 1st annual ACM SIGACT-SIGPLAN Symposium on Principles of Programming Languages (POPL '73), 41–51, [doi:10.1145/512927.512931](https://doi.org/10.1145/512927.512931).
- R. Nystrom, [*Crafting Interpreters*](https://craftinginterpreters.com/contents.html): part II builds a tree-walk interpreter, from scanning and parsing expressions to functions, and part III a bytecode virtual machine, with a chapter that compiles expressions with a Pratt parser and a chapter on closures.
