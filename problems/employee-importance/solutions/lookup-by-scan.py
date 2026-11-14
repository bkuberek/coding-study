def get_importance(employees: list[list[int]], employee_id: int) -> int:
    total = 0
    pending = [employee_id]
    while pending:
        wanted = pending.pop()
        record = next(record for record in employees if record[0] == wanted)
        total += record[1]
        pending.extend(record[2:])
    return total
