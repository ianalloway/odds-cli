"""Core odds math: conversions, Kelly criterion, EV, CLV calculations."""

from __future__ import annotations


def american_to_decimal(american: int) -> float:
    """Convert American odds to decimal odds.

    Args:
        american: American odds (e.g., -150, +200).

    Returns:
        Decimal odds (e.g., 1.667, 3.000).
    """
    if american > 0:
        return (american / 100.0) + 1.0
    elif american < 0:
        return (100.0 / abs(american)) + 1.0
    else:
        raise ValueError("American odds cannot be zero")


def decimal_to_american(decimal_odds: float) -> int:
    """Convert decimal odds to American odds.

    Args:
        decimal_odds: Decimal odds (e.g., 1.667, 3.000).

    Returns:
        American odds (e.g., -150, +200).
    """
    if decimal_odds < 1.0:
        raise ValueError("Decimal odds must be >= 1.0")
    if decimal_odds >= 2.0:
        return round((decimal_odds - 1.0) * 100)
    else:
        return round(-100.0 / (decimal_odds - 1.0))


def american_to_implied_prob(american: int) -> float:
    """Convert American odds to implied probability.

    Args:
        american: American odds (e.g., -150, +200).

    Returns:
        Implied probability as a float between 0 and 1 (e.g., 0.60, 0.333).
    """
    if american > 0:
        return 100.0 / (american + 100.0)
    elif american < 0:
        return abs(american) / (abs(american) + 100.0)
    else:
        raise ValueError("American odds cannot be zero")


def implied_prob_to_american(prob: float) -> int:
    """Convert implied probability to American odds.

    Args:
        prob: Implied probability between 0 and 1.

    Returns:
        American odds.
    """
    if prob <= 0.0 or prob >= 1.0:
        raise ValueError("Probability must be between 0 and 1 (exclusive)")
    if prob >= 0.5:
        return round(-100.0 * prob / (1.0 - prob))
    else:
        return round(100.0 * (1.0 - prob) / prob)


def decimal_to_implied_prob(decimal_odds: float) -> float:
    """Convert decimal odds to implied probability.

    Args:
        decimal_odds: Decimal odds (e.g., 1.667, 3.000).

    Returns:
        Implied probability as a float between 0 and 1.
    """
    if decimal_odds <= 0:
        raise ValueError("Decimal odds must be positive")
    return 1.0 / decimal_odds


def kelly_criterion(prob: float, american: int) -> float:
    """Calculate the Kelly criterion fraction for a bet.

    The Kelly criterion determines the optimal fraction of bankroll to wager
    to maximize long-term growth.

    Formula: f* = (bp - q) / b
        where b = decimal profit (decimal_odds - 1), p = prob of winning, q = 1 - p

    Args:
        prob: Your assessed probability of winning (0 to 1).
        american: The American odds being offered.

    Returns:
        Optimal fraction of bankroll to wager. Negative means no edge (don't bet).
    """
    if prob <= 0.0 or prob >= 1.0:
        raise ValueError("Probability must be between 0 and 1 (exclusive)")

    decimal_odds = american_to_decimal(american)
    b = decimal_odds - 1.0  # net profit per unit wagered
    p = prob
    q = 1.0 - prob

    kelly_fraction = (b * p - q) / b
    return kelly_fraction


def expected_value(prob: float, american: int, stake: float = 100.0) -> float:
    """Calculate the expected value of a bet.

    Args:
        prob: Your assessed true probability of winning (0 to 1).
        american: The American odds being offered.
        stake: The amount wagered (default $100).

    Returns:
        Expected value in dollars. Positive means +EV.
    """
    decimal_odds = american_to_decimal(american)
    profit = stake * (decimal_odds - 1.0)
    ev = (prob * profit) - ((1.0 - prob) * stake)
    return ev


def closing_line_value(opening_american: int, closing_american: int) -> float:
    """Calculate closing line value (CLV).

    CLV measures how much better your line was compared to the closing line.
    Positive CLV means you got a better price than the market settled at.

    Args:
        opening_american: The American odds when you placed the bet.
        closing_american: The closing American odds.

    Returns:
        CLV as a percentage. Positive = you beat the close.
    """
    opening_prob = american_to_implied_prob(opening_american)
    closing_prob = american_to_implied_prob(closing_american)

    # CLV = closing implied prob - opening implied prob
    # (for bets on the side you took; positive means you got better value)
    clv = closing_prob - opening_prob
    return clv * 100.0  # as percentage


def no_vig_probability(odds_side_a: int, odds_side_b: int) -> tuple[float, float]:
    """Remove the vig/juice to get true probabilities.

    Args:
        odds_side_a: American odds for side A.
        odds_side_b: American odds for side B.

    Returns:
        Tuple of (true_prob_a, true_prob_b) summing to 1.0.
    """
    implied_a = american_to_implied_prob(odds_side_a)
    implied_b = american_to_implied_prob(odds_side_b)

    total = implied_a + implied_b  # > 1.0 due to vig

    true_a = implied_a / total
    true_b = implied_b / total

    return (true_a, true_b)


def vig_percentage(odds_side_a: int, odds_side_b: int) -> float:
    """Calculate the vig/juice as a percentage.

    Args:
        odds_side_a: American odds for side A.
        odds_side_b: American odds for side B.

    Returns:
        Vig as a percentage (e.g., 4.5 means 4.5% vig).
    """
    implied_a = american_to_implied_prob(odds_side_a)
    implied_b = american_to_implied_prob(odds_side_b)

    overround = implied_a + implied_b - 1.0
    return overround * 100.0


def format_american(american: int) -> str:
    """Format American odds with a leading +/- sign.

    Args:
        american: American odds value.

    Returns:
        Formatted string like '+150' or '-200'.
    """
    if american > 0:
        return f"+{american}"
    else:
        return str(american)


def find_best_line(odds_by_book: dict[str, int], side: str = "back") -> tuple[str, int]:
    """Find the best available line across sportsbooks.

    Args:
        odds_by_book: Dict mapping book name to American odds.
        side: 'back' (want highest plus/lowest minus) or 'lay'.

    Returns:
        Tuple of (best_book_name, best_odds).
    """
    if side == "back":
        # For backing, we want the highest payout
        # Higher American odds = better for the bettor
        # +200 > +150 (obvious), -150 > -200 (less juice)
        best_book = max(odds_by_book, key=lambda k: odds_by_book[k])
    else:
        # For laying, we want the lowest payout to the other side
        best_book = min(odds_by_book, key=lambda k: odds_by_book[k])

    return (best_book, odds_by_book[best_book])


def parlay_odds(legs: list[int]) -> int:
    """Calculate combined American odds for a parlay.

    Args:
        legs: List of American odds for each leg.

    Returns:
        Combined American odds for the parlay.
    """
    combined_decimal = 1.0
    for american in legs:
        combined_decimal *= american_to_decimal(american)

    return decimal_to_american(combined_decimal)


def parlay_implied_prob(legs: list[int]) -> float:
    """Calculate implied probability of a parlay hitting.

    Args:
        legs: List of American odds for each leg.

    Returns:
        Combined implied probability.
    """
    combined_prob = 1.0
    for american in legs:
        combined_prob *= american_to_implied_prob(american)
    return combined_prob
