# Bank Project (Java)

## Statement

Build `Bank`, a set of bank accounts that hold whole amounts of money and send money to one another, as a small Java project. The API grows over four levels: each level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied. You keep the same code from one level to the next, so how you split it into classes and packages is part of the work.

Every method receives the current time as its first argument, `timestamp`, in milliseconds. The bank never reads a clock: the time is whatever the caller passes.

## Input

- `new Bank()`: creates a bank with no accounts.
- `timestamp`: the time of the call. Within one test, timestamps strictly increase from one call to the next.
- `accountId`, `sourceId`, `targetId`: account identifiers.
- `amount`: a positive amount of money.
- Each level's section describes the methods it adds and their other parameters.

## Output

Each method returns what its level describes. A failed call never throws an exception: it returns a sentinel, `-1` for a `long`, `""` for a `String` and `false` for a `boolean`.

## Project

`cstudy start` copies a small Java project, a Gradle build of its own, into `projects/bank-project-java/` in your workspace, and you solve the problem there, in as many classes and packages as you like:

- `src/main/java/bank/Bank.java`: the public class `Bank`, with level 1's methods throwing `UnsupportedOperationException`.
- `src/main/java/bank/Account.java`: an `Account` class to grow or replace.
- `src/test/java/bank/Level<n>Test.java`: the examples of each open level as JUnit 5 tests, written when the level opens and never rewritten. Edit them, and add your own test classes under `src/test/java/`.
- `README.md`, and the Gradle build: `settings.gradle.kts`, `build.gradle.kts`, `gradle.properties` and `gradle/wrapper/gradle-wrapper.properties`, which build with the workspace's JDK 21, Gradle and JUnit, offline. Keep them as they are.

The contract: `Bank` stays in `src/main/java/bank/Bank.java`, in package `bank`, public, with a public constructor that takes no arguments; and every method stays public and keeps the name, parameter types and return type its level gives. Each level starts with a line naming the methods it adds. Parameter names are yours.

`cstudy test bank-project-java` runs your tests, and so does `../../jvm/gradlew test` in the project folder, which is also how an IDE runs them; either run is feedback only. Gradle compiles every test class before it runs any, and a level's test class calls the methods that level adds, so no test runs until they all exist. `cstudy submit bank-project-java` compiles only `src/main/java` and grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so the code you change for a new level must keep their rules.

## Level 1: Accounts and transfers

- `createAccount(timestamp, accountId)`: opens an account with balance 0 and returns `true`. Returns `false` when the id is already taken.
- `deposit(timestamp, accountId, amount)`: adds `amount` to the account and returns its new balance, or `-1` when there is no such account.
- `transfer(timestamp, sourceId, targetId, amount)`: moves `amount` from the source account to the target account and returns the source's new balance. Returns `-1`, leaving both accounts as they were, when either account does not exist, when source and target are the same account, or when the source's balance is below `amount`.

### Example 1

<!-- case: ex1 -->

The second `createAccount` of `rosa` fails, and so does the deposit to `kim`, who never opened an account. `rosa` sends 250 of her 600 to `tom` and keeps 350, and a deposit of 50 brings `tom` to 300.

### Example 2

<!-- case: ex2 -->

`ada` cannot send 150 when she holds 100, and the refused transfer moves nothing: a deposit of 1 shows that `bo` received nothing. A transfer of her whole balance goes through and leaves her at 0.

## Level 2: Top spenders

- `topSpenders(timestamp, n)`: ranks the accounts by how much money has left them and returns the first `n` as strings `"<accountId>(<total>)"`. An account's total adds up its successful transfers; deposits and money received never count. Larger totals come first, and equal totals are ordered by account id, ascending, comparing the ids as `String.compareTo` does. When fewer than `n` accounts exist, every account is returned, including those whose total is 0.
- `1 <= n <= 1000`.

### Example 1

<!-- case: ex3 -->

`nia` sends 400 and then 300, 700 in all. `oz` sends 450, most of it money he had just received from `nia`; only what leaves an account counts, so his total is 450. `pam` only receives: her total is 0, so she comes last and is left out when `n` is 2.

### Example 2

<!-- case: ex4 -->

`una` and `eli` each send 20, so `eli` comes first by id. Asking for 10 accounts when only three exist returns all three.

## Level 3: Scheduled transfers

- `scheduleTransfer(timestamp, sourceId, targetId, amount, delay)`: books a transfer of `amount` from the source to the target, due at `timestamp + delay`. Returns its id `"transfer<k>"`, where `k` numbers the transfers booked successfully in the whole bank, starting at 1. Returns `""` and books nothing when either account does not exist or both are the same account. The source's balance is not checked when the transfer is booked.
- A booked transfer runs by itself. Every transfer due at time `t` runs before anything else happens in the first call whose timestamp is `t` or later, whatever that call does. When several are due by then, they run in order of due time, and transfers due at the same time run in the order they were booked. Each one takes effect at its due time, not at the time of the call that set it off.
- A transfer that runs moves the money exactly like `transfer`, and its amount counts toward the source's total in `topSpenders`. When the source's balance is below `amount` at the due time, the transfer is skipped: nothing moves, and it is never tried again.
- `cancelTransfer(timestamp, accountId, transferId)`: cancels a booked transfer before it runs, so it never runs. Only its source account may cancel it. Returns `true` on success, and `false` when the account does not exist, no transfer has that id, `accountId` is not the transfer's source, or the transfer has already run, been skipped or been cancelled.
- `1 <= delay <= 10^9`.

### Example 1

<!-- case: ex5 -->

`lou` books 30 for `max`, due at 24, and then 50, due at 10. The later booking falls due first: by the deposit at time 12, `max` has received the 50, and by the deposit at time 30 also the 30. Both count as money `lou` sent.

### Example 2

<!-- case: ex6 -->

`ann` books 50 for `raj`, due at 10, and `raj` books 5 for `ann`. `ann` cannot cancel `raj`'s booking; `raj` can. At time 10 the 50 fall due before `ann`'s deposit, while she holds 40, so that transfer is skipped: her deposit brings her to 41, and `raj` receives nothing.

## Level 4: Merges and balance history

- `mergeAccounts(timestamp, accountId, otherId)`: folds `otherId` into `accountId`. The balance and the spending total of `otherId` are added to those of `accountId`, and every booked transfer still waiting to run that names `otherId` as its source or its target names `accountId` there instead, so `accountId` can cancel the ones it now sends. Afterwards `otherId` no longer exists, and an id that disappeared in a merge is never created again. Returns `false` and changes nothing when the ids are equal or either account does not exist.
- A transfer that falls due when its source and target are the same account, as a transfer waiting between two merged accounts becomes, is skipped like one the source cannot pay.
- `getBalance(timestamp, accountId, timeAt)`: the balance the account had at time `timeAt`, after every call with a timestamp at most `timeAt` and every scheduled transfer due by then. Returns `-1` when the account did not exist at `timeAt`: before it was created, or from the moment it was merged away. The kept account's balance includes the absorbed balance only from the merge on, and the merged-away account still answers for times before the merge.
- `timeAt` is never later than `timestamp`.

### Example 1

<!-- case: ex7 -->

`work` has sent 30 and booked 40 for `shop` when it is merged into `home` at time 8: `home` now holds 200 + 50 and has sent 30. `work` no longer takes deposits, and its booking leaves from `home` at time 20, so `shop` holds 30 + 40 before its deposit of 1. The ranking lists `home` with 70 and no longer `work`.

### Example 2

<!-- case: ex8 -->

`joy` books 60 for `kip`, due at 12, and absorbs `kip` at time 15. History knows that `joy` did not exist at time 4, held 100 at time 11, 40 at time 12 when the transfer ran, and 40 + 65 from the merge on. `kip` held 65 at time 14 and is gone at time 15.

## Constraints

- At most 1000 calls per test.
- `1 <= timestamp <= 10^9`, strictly increasing within a test.
- `1 <= amount <= 10^10`; balances stay below `2^53`, well within a `long` and beyond an `int`.
- Account ids are 1 to 10 lowercase letters or digits.

## Follow-ups

- Two debits of the same account that arrive at the same moment can both see enough money and overdraw it together. How would you prevent that: a row lock, a conditional update such as `UPDATE ... SET balance = balance - :amount WHERE balance >= :amount`, or a version check with retries? And if `Bank` itself were called from several threads, would you make its methods `synchronized`, guard it with a `ReentrantLock`, or lock each account, and in which order would a transfer take two account locks?
- Which parts of your design would you test on their own, without going through `Bank`, and what would those tests pin down that the level examples do not?
- If the bank had to survive a restart, what would you store: the balances, the changes that produced them, or both?

## Hints

### Hint 1

Give each account a class that owns its numbers, with methods for the rules that change them, and keep `Bank` to looking accounts up, checking the request and delegating. Each later level then adds a field, a method or a class instead of a rewrite.

### Hint 2

Check every reason a call can fail before you change anything. A failed call must leave every account exactly as it was, which is easy to get wrong when one call touches two accounts.

### Hint 3

When something has to happen at a time of its own rather than at a call, let time move in exactly one place: a private step at the start of every public method, read-only ones included, that catches the bank up to the call's timestamp. Items due at different times must come out in due-time order, which is not always the order they arrived in. A `java.util.PriorityQueue` with a `Comparator` on the due time, then on an arrival number, hands them out in the right order; without the second key, items due at the same time come out in whatever order the heap left them. An item that is called off can stay in the queue, marked, until it reaches the head.

### Hint 4

To answer questions about the past, record each change at the moment it took effect, the due time for anything that ran later, and search that record. When accounts are combined, remember where each old id went and follow that link when you need it, instead of rewriting everything that mentions it.
