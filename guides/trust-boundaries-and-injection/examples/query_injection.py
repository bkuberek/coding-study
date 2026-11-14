"""Untrusted text crossing into a SQL interpreter: glued into the query, then bound as a value."""

import sqlite3

db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, customer TEXT, item TEXT, total INTEGER)")
db.executemany(
    "INSERT INTO orders (customer, item, total) VALUES (?, ?, ?)",
    [("mia", "lamp", 40), ("mia", "desk", 220), ("raj", "chair", 95), ("d'arcy", "rug", 130)],
)


def glued(customer: str) -> list:
    """Builds the SQL text from the input: the input can end the string and add SQL of its own."""
    return db.execute("SELECT customer, item FROM orders WHERE customer = '" + customer + "'").fetchall()


def bound(customer: str) -> list:
    """Sends the SQL and the value apart: the value can only ever be a value."""
    return db.execute("SELECT customer, item FROM orders WHERE customer = ?", (customer,)).fetchall()


for text in ["raj", "x' OR 1=1 --", "d'arcy"]:
    for query in (glued, bound):
        try:
            answer = query(text)
        except sqlite3.Error as error:
            answer = f"error: {error}"
        print(f"{query.__name__:6} {text!r:15} {answer}")

# A placeholder stands for a value, never for a column name or a keyword such as DESC.
# So a sort order chosen by the user is looked up in a fixed table of SQL the code wrote.
SORTS = {"newest": "id DESC", "biggest": "total DESC", "item": "item"}


def sorted_items(choice: str) -> list:
    order = SORTS.get(choice)
    if order is None:
        return [f"refused: unknown sort {choice!r}"]
    return [item for (item,) in db.execute(f"SELECT item FROM orders ORDER BY {order}")]


print(sorted_items("biggest"))
print(sorted_items("total; DROP TABLE orders"))
