"""Two pointers: from both ends toward each other, and one per list in the same direction."""


def reverse_in_place(values: list[int]) -> None:
    """Swap the two ends, then move both pointers inward, until they meet."""
    i, j = 0, len(values) - 1
    while i < j:  # i == j is the middle of an odd length: nothing to swap
        print(f"  i={i} j={j}: swap {values[i]} and {values[j]}")
        values[i], values[j] = values[j], values[i]
        i, j = i + 1, j - 1
    print(f"  i={i} j={j}: stop")


def merge(first: list[int], second: list[int]) -> list[int]:
    """One pointer per sorted list; take the smaller front value each time."""
    i = j = 0
    merged: list[int] = []
    while i < len(first) and j < len(second):
        if first[i] <= second[j]:  # on a tie, take from first: equal values keep their order
            print(f"  i={i} j={j}: {first[i]} <= {second[j]}, take {first[i]} from the first list")
            merged.append(first[i])
            i += 1
        else:
            print(f"  i={i} j={j}: {first[i]} > {second[j]}, take {second[j]} from the second list")
            merged.append(second[j])
            j += 1
    print(f"  one list is used up; append the rest: {first[i:] + second[j:]}")
    merged += first[i:] + second[j:]  # at most one of the two slices is non-empty
    return merged


values = [3, 8, 1, 9, 4, 7]
print("reverse", values)
reverse_in_place(values)
print("result:", values)

odd = [1, 2, 3, 4, 5]
builtin = odd.copy()
builtin.reverse()  # the list method also works in place, and returns None
print("reverse", odd)
reverse_in_place(odd)
print("result:", odd, "| list.reverse agrees:", odd == builtin)

print("merge [2, 5, 9] and [3, 4, 10, 12]")
print("result:", merge([2, 5, 9], [3, 4, 10, 12]))
