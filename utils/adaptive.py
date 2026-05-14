from statistics import mean
from datetime import date, timedelta


def suggest_next_difficulty(recent_scores: list[float]) -> str:
    if not recent_scores:
        return "easy"
    avg = mean(recent_scores[-3:])
    if avg >= 80:
        return "hots"
    if avg >= 60:
        return "medium"
    return "easy"


def calculate_xp(score: float, difficulty: str) -> int:
    base = {"easy": 5, "medium": 10, "hots": 20}
    return round(base.get(difficulty, 5) * (score / 100))


def update_streak(user) -> int:
    today = date.today()
    if user.last_active_date == today:
        return user.streak_days
    if user.last_active_date == today - timedelta(days=1):
        return user.streak_days + 1
    return 1


def calc_activity_score(quiz_count: int, avg_score: float) -> int:
    if quiz_count == 0:
        return 0
    return min(round((quiz_count / 5) * 50 + avg_score * 0.5), 100)
