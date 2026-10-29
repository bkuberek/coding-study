def get_importance(employees: list[list[int]], employee_id: int) -> int:
    by_id = {record[0]: record for record in employees}
    total = 0
    pending = [employee_id]
    while pending:
        record = by_id[pending.pop()]
        total += record[1]
        pending.extend(record[2:])
    return total
