# Accounts Merge

## Statement

You get a list of user accounts. Each account is a list whose first entry is the owner's name and whose other entries are email addresses. Two accounts belong to the same person exactly when they share at least one email address, directly or through a chain of accounts that each share an address with the next. Accounts with the same name but no such link belong to different people, since people can share a name. All accounts of one person carry the same name.

Merge the accounts of each person into one: the person's name followed by all of their distinct email addresses in sorted order.

Reference: this is our own wording of LeetCode problem 721, [Accounts Merge](https://leetcode.com/problems/accounts-merge/).

## Input

- `accounts`: each entry is `[name, email, email, ...]`

## Output

One list per person: the name, then every distinct email address of that person sorted in ascending order of character codes (the plain string order of Python, Java, Kotlin and JavaScript for these characters). The merged accounts may come in any order.

## Examples

### Example 1

<!-- case: ex1 -->

The first and third accounts share `ada.l@work.org`, so they belong to one person, whose three addresses are listed once each and sorted (`.` sorts before `@`). The last account is also named Ada but shares no address with the others, so it stays separate, and Bo's account is unchanged.

### Example 2

<!-- case: ex2 -->

The first two accounts share nothing, but the third shares `k2@a.com` with the first and `k3@a.com` with the second, which links all three into one person.

## Constraints

- `1 <= accounts.length <= 1000`
- `2 <= accounts[i].length <= 10`
- `accounts[i][0]` is a name of 1 to 10 English letters.
- Every email address has 3 to 30 characters: lowercase letters, digits, `@` and `.`.
- An account may list the same address more than once.
- Accounts that share an address have the same name.

## Follow-ups

- What are the nodes of the graph here: accounts, email addresses, or both? Which choice keeps the graph smallest?
- Can you merge while reading the input once, without building adjacency lists?

## Hints

### Hint 1

Treat accounts as nodes and join two of them whenever they share an address. Each person is one connected component.

### Hint 2

You do not need to compare every pair of accounts: remember the first account that listed each address, and join every later account that lists it with that first one.

### Hint 3

With union-find over the account indexes, each address costs one union. Afterwards, collect the addresses by the root of their account, sort each group and put the name in front.
