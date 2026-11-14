def rank_players(names: list[str], scores: list[int]) -> list[str]:
    players = sorted(zip(names, scores, strict=True), key=lambda player: (-player[1], player[0]))
    return [name for name, _ in players]
