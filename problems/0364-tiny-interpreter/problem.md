# Tiny Interpreter

## Statement

Build `Interpreter`, which runs programs written in a small expression language: integers, arithmetic, `let`, `if`, and functions that can capture variables and call themselves. You build it the way real language implementations are built, in stages, and each level adds one stage. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**From text to a value.** A program arrives as text. Before anything can run, the text is cut into tokens, the words of the language: `let x = 2 in x * 3` is the keyword `let`, the name `x`, the symbol `=`, the number `2`, and so on. That is the job of a tokenizer (also called a lexer or scanner), level 1. A parser then reads the tokens and builds a syntax tree, a tree that records how the parts of the program belong together: the `let` has a name, a value and a body, and the body is a multiplication of `x` by `3`. The parser must know that `1 + 2 * 3` multiplies first, which is precedence, and that `10 - 4 - 3` subtracts from the left, which is associativity. That is level 2. Level 3 walks the tree and computes the value; level 4 translates the tree into instructions for a small machine and runs those instead.

```text
let x = 2 in x * 3

tokens:  keyword let | name x | symbol = | number 2 | keyword in | name x | symbol * | number 3

tree:        let
           /  |   \
          x   2    *
                  / \
                 x   3

value:   6
```

Aim to finish in 150 minutes. A good split: read the statement in the first 15 minutes, then finish level 1 by about minute 35, level 2 by 70, level 3 by 105 and level 4 by 140, keeping the last minutes for a final run.

## Input

- `Interpreter(maxDepth)`: creates an interpreter. `maxDepth` is used from level 3 on: it is the most function calls that may be in progress at once.
- `source`: the text of a program.
- A position in the source is written `line:column`. Both count from 1: the first character of the source is at `1:1`. A newline ends a line, and the character after it is at column 1 of the next line. Every other character, a tab included, takes one column.
- Each level's section describes the methods it adds.

## Output

Every method returns text, or a list of texts. When the source cannot be handled, the result is an error written `error <code> <line>:<column>`, such as `error bad-char 1:5`: a fixed code and the position where the problem was found. Each level lists the codes it adds and the position each one reports. A method that returns a list returns a list holding just that one error.

## Level 1: Tokens

- `tokenize(source)`: the tokens of `source`, each written `<kind> <text> <line>:<column>` with the position of its first character, followed by one last token written `end <line>:<column>`, the position just after the last character of the source.

The tokenizer reads the source from left to right:

- **Whitespace** (space, tab and newline) separates tokens and is otherwise skipped.
- **Comments** start with `#` and run to the end of the line. They are skipped.
- **Numbers** are runs of digits `0` to `9`, of kind `number`. A number must not start with `0` unless it is just `0`, and must be at most 2147483647; otherwise it is the error `bad-number` at its first digit. `12ab` is the number `12` followed by the name `ab`.
- **Names** start with a letter (`a` to `z`, `A` to `Z`) or `_`, followed by letters, digits and `_`. The six names `let`, `in`, `fn`, `if`, `then` and `else` are of kind `keyword`; every other one is of kind `name`.
- **Symbols** are of kind `symbol`: `(` `)` `,` `+` `-` `*` `/` `%` `^` `<` `>` `=` and the two-character `==` `!=` `<=` `>=` `=>`. When two characters form a two-character symbol, they are one token: `a>=b` is `a`, `>=`, `b`, and `==>` is `==` then `>`.
- **Anything else**, such as `$`, a lone `!`, a quote, a carriage return or a letter outside `a` to `z` and `A` to `Z`, is the error `bad-char` at that character.

The first error stops the tokenizer: the result is that error alone.

### Example 1

<!-- case: ex1 -->

Seven tokens: `let` and `in` are keywords. The `end` token sits at column 16, just after the last `x`.

### Example 2

<!-- case: ex2 -->

`>=` is one symbol, the comment is skipped, and the newline at the end puts the `end` token at `2:1`. In the second source, `$` is not part of the language.

## Level 2: A syntax tree

- `parse(source)`: the syntax tree of the program, written as described below, or an error.

**The grammar.** A program is one expression, and an expression is one of these:

| Form | Meaning |
|------|---------|
| `42`, `x` | a number or a name |
| `( e )` | parentheses only group: they do not appear in the tree |
| `- e` | negation |
| `a + b` and the other binary operators | arithmetic or a comparison |
| `f(a, b)` | a call: any expression followed by arguments in parentheses, possibly none: `f()` |
| `let x = e1 in e2` | a variable `x` holding the value of `e1`, used in `e2` |
| `if c then a else b` | a choice |
| `fn (a, b) => e`, `fn name(a, b) => e` | a function, without or with a name; it may have no parameters: `fn () => 1` |

**Precedence and associativity**, from the tightest to the loosest:

| Level | Operators | Groups |
|-------|-----------|--------|
| 1 | a call `f(...)` | from the left: `f(1)(2)` calls the result of `f(1)` |
| 2 | `^` (power) | from the right: `2 ^ 3 ^ 2` is `2 ^ (3 ^ 2)` |
| 3 | `-` in front of an expression | `-2 ^ 2` is `-(2 ^ 2)`, while `2 * -3` and `2 ^ -1` are allowed |
| 4 | `*` `/` `%` | from the left |
| 5 | `+` `-` | from the left: `10 - 4 - 3` is `(10 - 4) - 3` |
| 6 | `==` `!=` `<` `<=` `>` `>=` | from the left |

`let`, `if` and `fn` can start an expression anywhere one can start, even right after an operator, and the expression after their last keyword or `=>` extends as far to the right as it can: `1 + let x = 2 in x * 3` is `1 + (let x = 2 in (x * 3))`, and `fn (x) => x + 1` is a function whose body is `x + 1`.

**Writing the tree.** Numbers and names are written as they are. Everything else is written in parentheses, the kind first and then its parts, separated by single spaces:

| Form | Written |
|------|---------|
| `a + b` (any binary operator) | `(+ a b)` |
| `- e` | `(neg e)` |
| `f(a, b)` | `(call f a b)`, and `(call f)` with no arguments |
| `let x = e1 in e2` | `(let x e1 e2)` |
| `if c then a else b` | `(if c a b)` |
| `fn (a, b) => e` | `(fn (a b) e)`, and `(fn () e)` with no parameters |
| `fn name(a, b) => e` | `(fn name (a b) e)` |

**Errors.** Tokenizing comes first, so a source with a tokenizer error returns that error. Otherwise:

- `unexpected-token`: reading the tokens from the left, the first token at which the program can no longer be completed, such as a `)` with nothing to close, a missing `then`, or a token after a complete program. The position is that token's, the `end` token included.
- `duplicate-param`: a parameter name used twice in one function, at the second one. Any `unexpected-token` before it is reported first.

### Example 1

<!-- case: ex3 -->

`*` binds tighter than `+` and `-`, and the two subtractions group from the left. `^` groups from the right, and the minus applies to `2 ^ 2`, not to `2`.

### Example 2

<!-- case: ex4 -->

The `let` holds a function and calls it. In `f(1 2)`, the `2` cannot follow `1` inside an argument list, so the error is at the `2`.

## Level 3: Evaluation with closures

- `evaluate(source)`: the value of the program, or an error. An integer is written in decimal, with a `-` when negative. A function is written `<fn name>`, or `<fn>` when it has no name.

**Values.** A value is an integer between -2147483648 and 2147483647, or a function.

**Names and scope.** `let x = e1 in e2` computes `e1`, then computes `e2` with `x` holding that value. Inside `e2`, `x` hides any outer `x`, and `e1` itself still sees the outer one, so `let x = 1 in let x = x + 1 in x` is 2. A name that no enclosing `let`, parameter or function name defines is the error `unbound` at that name.

**Functions and closures.** A `fn` expression does not run anything: its value is a function that remembers the names visible where the `fn` was written. That pairing of code and remembered names is called a closure. For example, in `let add = fn (a) => fn (b) => a + b in add(2)(40)`, the call `add(2)` returns the inner function, which remembers `a = 2`; calling it with `40` gives `42`, although the call that set `a` has already finished. Names are looked up where the function was written (lexical scope), never where it is called from, so `let x = 1 in let f = fn () => x in let x = 2 in f()` is 1.

**Calls.** For `f(a1, ..., an)`, compute `f`, then the arguments from left to right, then check, in this order, at the position of the `(`:

1. `f` is not a function: `not-callable`.
2. `n` differs from the number of parameters: `arity`.
3. `maxDepth` calls are already in progress: `depth`. A call is in progress from the moment it starts until its body has a value, so a function that calls itself `k` times in a row needs `maxDepth >= k + 1` for the first call and the `k` inside it.

Then the body is computed with the remembered names, plus the function's own name (when it has one) meaning the function itself, which is how a function calls itself, plus the parameters holding the arguments. A parameter with the same name as the function hides the function's name. The function's name is visible only inside its body: `let f = fn g(n) => n in g(1)` is the error `unbound` at the last `g`.

**Operators.** Both operands are computed, left first, before the operator is applied; `-e` computes `e` first. Then:

- An operand that is a function is the error `type` at the operator.
- `/` divides and drops the fraction, rounding towards zero: `7 / 2` is 3 and `-7 / 2` is -3. `%` is the remainder that goes with it, with the sign of the left operand: `-7 % 2` is -1 and `7 % -2` is 1. A right operand of 0 is `div-zero` at the operator.
- `a ^ b` is the product of `b` copies of `a`, so `a ^ 0` is 1, `0 ^ 0` included. A negative `b` is `negative-exponent` at the operator.
- The comparisons give 1 when they hold and 0 when not.
- A result outside the range of values is `overflow` at the operator, for `-` in front of an expression too: `-(-2147483647 - 1)` overflows.

**Choices.** `if c then a else b` computes `c`; if it is a function, that is the error `type` at the `if`. When `c` is not 0, the result is `a`, otherwise `b`, and the other branch is not computed.

The first error stops the program: the result is that error.

### Example 1

<!-- case: ex5 -->

`double` doubles its argument. `add(5)` returns a function that remembers `a = 5`, and `add5(10)` adds 10 to it.

### Example 2

<!-- case: ex6 -->

With `maxDepth = 15`, `fact(5)` needs 5 calls in progress at its deepest and succeeds. `fact(20)` would need 20, so the sixteenth nested call fails with `depth`, at the `(` of `fact(n - 1)`. `fact(13)` stays within the depth, but 13! is larger than 2147483647, so a multiplication overflows, at the `*`.

## Level 4: Bytecode and a stack machine

The tree walker of level 3 follows the tree, and each function call in the program becomes a call in your own language, so deep recursion in a program needs deep recursion in the interpreter. Most language runtimes instead compile the tree into bytecode, a flat list of simple instructions, and run it on a virtual machine: a loop that reads one instruction at a time and keeps its intermediate values on a stack. `1 + 2 * 3` becomes:

```text
0 PUSH 1        stack: 1
1 PUSH 2        stack: 1 2
2 PUSH 3        stack: 1 2 3
3 MUL 1:7       stack: 1 6
4 ADD 1:3       stack: 7
5 RETURN        the result is 7
```

- `bytecode(source)`: the bytecode of the program as a listing, or an error.
- `run(source)`: compiles the program and runs the bytecode on the machine described below. Its result must be exactly what `evaluate` returns for the same source and `maxDepth`, errors and positions included.

**Blocks.** The program is block 0, and the body of each `fn` expression is a block of its own, numbered 1, 2, 3 and so on in the order their `fn` keywords appear in the source. Each block is a list of instructions numbered from 0, ending with `RETURN`.

**Instructions.** Each instruction is written as its index, its name, its operand when it has one, and a position when it can fail, all separated by single spaces: `3 JUMP_IF_ZERO 7 1:1`.

| Instruction | Operand | Position | Effect |
|-------------|---------|----------|--------|
| `PUSH n` | an integer | none | push `n` |
| `LOAD x` | a name | of the name | push the value of `x`, or fail with `unbound` |
| `NEG` | none | of the `-` | pop a value, push its negation |
| `ADD` `SUB` `MUL` `DIV` `MOD` `POW` | none | of the operator | pop the right operand, then the left one, push the result of `+` `-` `*` `/` `%` `^` |
| `EQ` `NE` `LT` `LE` `GT` `GE` | none | of the operator | the same for `==` `!=` `<` `<=` `>` `>=` |
| `JUMP_IF_ZERO k` | an index | of the `if` | pop the condition; when it is 0, continue at instruction `k` of this block |
| `JUMP k` | an index | none | continue at instruction `k` of this block |
| `BIND x` | a name | none | pop a value and make `x` hold it, hiding any outer `x` |
| `UNBIND` | none | none | end the innermost `BIND` of this call |
| `CLOSURE k` | a block number | none | push the function of block `k`, remembering the names visible now |
| `CALL n` | an argument count | of the `(` | pop `n` arguments, then the function below them, and call it |
| `RETURN` | none | none | the value on top of the stack is the block's result |

Every failure has the same code and position as in level 3.

**From tree to bytecode.** Each form is compiled exactly as follows, where `[e]` stands for the instructions of `e`:

| Form | Instructions |
|------|--------------|
| a number `n` | `PUSH n` |
| a name `x` | `LOAD x` |
| `- e` | `[e]` `NEG` |
| `a + b` and the other binary operators | `[a]` `[b]` then the operator's instruction |
| `f(a1, ..., an)` | `[f]` `[a1]` ... `[an]` `CALL n` |
| `let x = e1 in e2` | `[e1]` `BIND x` `[e2]` `UNBIND` |
| `if c then a else b` | `[c]` `JUMP_IF_ZERO` to the first instruction of `[b]`, then `[a]` `JUMP` to just after `[b]`, then `[b]` |
| `fn ...` | `CLOSURE k`, where `k` is the number of its block |

**The listing.** Blocks in increasing order. Each block starts with a header line, `block 0 main` for the program and, for a function, `block <k>` followed by the head of its tree from level 2: `block 1 fn fact (n)` or `block 2 fn (a b)`. The block's instructions follow, one per line.

**The machine.** It has one stack of values and a stack of frames. A frame is one block being run: its instruction index and the names visible in it. The program starts in a frame for block 0 with no names. `CALL` checks the function, the argument count and the depth exactly as level 3 does, where the calls in progress are the frames other than the program's, and then starts a frame for the function's block, with the names the function remembered, the function's own name and its parameters. `RETURN` ends the frame, and the value on top of the stack becomes the value of the `CALL` in the frame below; when the program's frame returns, that value is the result. The machine loop never calls itself, so the depth of the program's recursion is limited only by `maxDepth`.

### Example 1

<!-- case: ex7 -->

The listing of the example above, and its result. In the second program, `BIND` gives the 5 a name and `UNBIND` ends that name after the body.

### Example 2

<!-- case: ex8 -->

The function is block 1. Block 0 makes the closure, names it `sq`, loads it and calls it with 4. The call runs block 1, whose `RETURN` leaves 16 for block 0.

## Constraints

- At most 20 calls per test.
- `1 <= maxDepth <= 100`.
- A source holds at most 2,000 characters.
- The syntax tree of a source that parses is at most 15 levels deep: the whole program is level 1, and each part of a form (an operand, the function or an argument of a call, the value or body of a `let`, the condition or a branch of an `if`, the body of a `fn`) is one level below the form. Parentheses nest at most 15 deep.
- Together with `maxDepth`, this keeps a tree walker's recursion within about 1,500 levels: at most 100 calls in progress, each at most 15 levels into the tree.
- Running a program takes at most 50,000 function calls.

## Follow-ups

- Every `LOAD` here searches the names by text, scope after scope. A compiler can decide at compile time where each name lives and emit `LOAD_LOCAL 2` or `LOAD_CAPTURED 0 1` instead. What must happen to a captured variable when the call that created it returns?
- Add `&&` and `||` that compute their right side only when needed. Which instructions do they compile to?
- A function whose last action is calling another function does not need to keep its frame. How would `CALL` change to make such tail calls run in constant frame depth, and what happens to the `depth` error?
- How would you report several syntax errors in one pass instead of stopping at the first?

## Hints

### Hint 1

Write the tokenizer as a loop over an index into the source, with a line and a column counter beside it. Look at the current character to decide what kind of token starts here, then read as many characters as belong to that token. For symbols, try the two-character ones before the one-character ones.

### Hint 2

For parsing, write one function that parses an expression. It first parses something that can start an expression (a number, a name, `(`, `-`, `let`, `if`, `fn`), then looks at the next token: if it is an operator that should bind into this expression, it consumes it, parses the right side, and repeats with the bigger expression as the new left side.

### Hint 3

Give each binary operator a number, its binding power, and pass a minimum to the expression function: it only takes operators whose power is greater than the minimum. Parse the right side of a left-grouping operator with its own power as the minimum, and the right side of `^` with one less, so that a second `^` still binds into it. Negation parses its operand with a minimum between `*` and `^`. This technique is top-down operator precedence, also called Pratt parsing.

### Hint 4

For evaluation, represent the names in scope as a chain of small maps, each pointing to the enclosing one. `let` and calls add a new map in front of an existing chain; looking up a name walks the chain. A function value is its parameters, its body and the chain that was current where the `fn` was evaluated.

### Hint 5

Pass the number of calls in progress down through your evaluation function, and add one when you enter a function's body. Check the callee, the argument count and that number in the order the statement gives, after computing the arguments.

### Hint 6

For the compiler, emit instructions into the current block's list as you walk the tree. For `if`, emit `JUMP_IF_ZERO` with a placeholder target, and fill in its target once you know where the `else` branch starts; do the same for `JUMP`. Number a function's block when you meet its `fn` keyword, before compiling its body.

### Hint 7

For the machine, keep a list of frames, each with its block, instruction index and chain of names, and loop: take the instruction at the top frame's index, advance the index, and act on it. `CALL` pushes a frame; `RETURN` pops one and leaves the value on the shared stack for the caller. Reuse the level 3 functions for operators, conditions and call checks, so that both paths produce the same errors.
