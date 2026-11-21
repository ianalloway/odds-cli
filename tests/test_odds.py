"""Tests for odds_cli.odds — core odds math functions."""

import pytest
from odds_cli.odds import (
    american_to_decimal,
    decimal_to_american,
    american_to_implied_prob,
    implied_prob_to_american,
    decimal_to_implied_prob,
    kelly_criterion,
    expected_value,
    closing_line_value,
    no_vig_probability,
    vig_percentage,
    format_american,
    find_best_line,
    parlay_odds,
    parlay_implied_prob,
)


class TestAmericanToDecimal:
    def test_positive_odds(self):
        assert american_to_decimal(200) == pytest.approx(3.0)

    def test_positive_odds_150(self):
        assert american_to_decimal(150) == pytest.approx(2.5)

    def test_negative_odds(self):
        assert american_to_decimal(-200) == pytest.approx(1.5)

    def test_negative_odds_150(self):
        assert american_to_decimal(-150) == pytest.approx(1.6667, rel=1e-3)

    def test_even_money_plus(self):
        assert american_to_decimal(100) == pytest.approx(2.0)

    def test_even_money_minus(self):
        assert american_to_decimal(-100) == pytest.approx(2.0)

    def test_zero_raises(self):
        with pytest.raises(ValueError):
            american_to_decimal(0)


class TestDecimalToAmerican:
    def test_plus_odds(self):
        assert decimal_to_american(3.0) == 200

    def test_minus_odds(self):
        assert decimal_to_american(1.5) == -200

    def test_even_money(self):
        assert decimal_to_american(2.0) == 100

    def test_below_one_raises(self):
        with pytest.raises(ValueError):
            decimal_to_american(0.5)


class TestAmericanToImpliedProb:
    def test_favorite(self):
        # -200 implies 66.67%
        assert american_to_implied_prob(-200) == pytest.approx(0.6667, rel=1e-3)

    def test_underdog(self):
        # +200 implies 33.33%
        assert american_to_implied_prob(200) == pytest.approx(0.3333, rel=1e-3)

    def test_even_money(self):
        assert american_to_implied_prob(100) == pytest.approx(0.5)
        assert american_to_implied_prob(-100) == pytest.approx(0.5)

    def test_heavy_favorite(self):
        # -500 implies 83.33%
        assert american_to_implied_prob(-500) == pytest.approx(0.8333, rel=1e-3)

    def test_long_shot(self):
        # +500 implies 16.67%
        assert american_to_implied_prob(500) == pytest.approx(0.1667, rel=1e-3)

    def test_zero_raises(self):
        with pytest.raises(ValueError):
            american_to_implied_prob(0)


class TestImpliedProbToAmerican:
    def test_favorite(self):
        assert implied_prob_to_american(0.6667) == pytest.approx(-200, abs=2)

    def test_underdog(self):
        assert implied_prob_to_american(0.3333) == pytest.approx(200, abs=2)

    def test_even_money(self):
        assert implied_prob_to_american(0.5) == pytest.approx(-100, abs=2)

    def test_invalid_zero(self):
        with pytest.raises(ValueError):
            implied_prob_to_american(0.0)

    def test_invalid_one(self):
        with pytest.raises(ValueError):
            implied_prob_to_american(1.0)


class TestDecimalToImpliedProb:
    def test_basic(self):
        assert decimal_to_implied_prob(2.0) == pytest.approx(0.5)

    def test_favorite(self):
        assert decimal_to_implied_prob(1.5) == pytest.approx(0.6667, rel=1e-3)

    def test_underdog(self):
        assert decimal_to_implied_prob(3.0) == pytest.approx(0.3333, rel=1e-3)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            decimal_to_implied_prob(0)


class TestKellyCriterion:
    def test_positive_edge(self):
        # 60% chance at -110 odds (decimal 1.909)
        # b = 0.909, p = 0.6, q = 0.4
        # kelly = (0.909 * 0.6 - 0.4) / 0.909 = 0.1584
        kf = kelly_criterion(0.6, -110)
        assert kf > 0
        assert kf == pytest.approx(0.1584, rel=0.02)

    def test_no_edge(self):
        # 50% chance at -110 odds = negative kelly
        kf = kelly_criterion(0.5, -110)
        assert kf < 0

    def test_big_underdog_edge(self):
        # 40% chance at +200 odds
        # b = 2.0, p = 0.4, q = 0.6
        # kelly = (2.0 * 0.4 - 0.6) / 2.0 = 0.1
        kf = kelly_criterion(0.4, 200)
        assert kf == pytest.approx(0.1)

    def test_invalid_prob(self):
        with pytest.raises(ValueError):
            kelly_criterion(0.0, -110)
        with pytest.raises(ValueError):
            kelly_criterion(1.0, -110)


class TestExpectedValue:
    def test_positive_ev(self):
        # 55% at -110 on $100
        ev = expected_value(0.55, -110, 100.0)
        assert ev > 0

    def test_negative_ev(self):
        # 45% at -110 on $100
        ev = expected_value(0.45, -110, 100.0)
        assert ev < 0

    def test_fair_line(self):
        # 50% at +100 = 0 EV
        ev = expected_value(0.5, 100, 100.0)
        assert ev == pytest.approx(0.0)


class TestClosingLineValue:
    def test_positive_clv(self):
        # Got +150, closed at +120 = you got better value
        clv = closing_line_value(150, 120)
        assert clv > 0

    def test_negative_clv(self):
        # Got -150, closed at -120 = market moved against you
        clv = closing_line_value(-150, -120)
        assert clv < 0


class TestNoVigProbability:
    def test_sums_to_one(self):
        p_a, p_b = no_vig_probability(-110, -110)
        assert p_a + p_b == pytest.approx(1.0)
        assert p_a == pytest.approx(0.5)
        assert p_b == pytest.approx(0.5)

    def test_favorite_underdog(self):
        p_a, p_b = no_vig_probability(-200, 170)
        assert p_a + p_b == pytest.approx(1.0)
        assert p_a > p_b  # favorite has higher true prob


class TestVigPercentage:
    def test_standard_vig(self):
        # -110 / -110 = about 4.76% vig
        vig = vig_percentage(-110, -110)
        assert vig == pytest.approx(4.76, rel=0.02)

    def test_no_vig(self):
        # +100 / +100 = 0% vig (theoretical)
        # Actually this sums to 1.0 exactly, so vig = 0
        vig = vig_percentage(100, -100)
        assert vig == pytest.approx(0.0, abs=0.1)


class TestFormatAmerican:
    def test_positive(self):
        assert format_american(200) == "+200"

    def test_negative(self):
        assert format_american(-150) == "-150"

    def test_negative_100(self):
        assert format_american(-100) == "-100"


class TestFindBestLine:
    def test_find_highest(self):
        books = {"DK": 150, "FD": 155, "MGM": 145}
        book, odds = find_best_line(books)
        assert book == "FD"
        assert odds == 155

    def test_find_least_negative(self):
        books = {"DK": -170, "FD": -175, "MGM": -165}
        book, odds = find_best_line(books)
        assert book == "MGM"
        assert odds == -165


class TestParlayOdds:
    def test_two_leg(self):
        # +100 * +100 = 3.0 decimal = +200
        result = parlay_odds([100, 100])
        assert result == 300  # 2.0 * 2.0 = 4.0 decimal = +300

    def test_single_leg(self):
        result = parlay_odds([-150])
        assert result == decimal_to_american(american_to_decimal(-150))


class TestParlayImpliedProb:
    def test_two_legs(self):
        # Two 50/50 bets = 25%
        prob = parlay_implied_prob([100, -100])
        assert prob == pytest.approx(0.25)

    def test_single_leg(self):
        prob = parlay_implied_prob([-200])
        assert prob == pytest.approx(american_to_implied_prob(-200))


# ─── Additional edge-case and regression tests ────────────────────────────────

class TestAmericanToDecimalEdgeCases:
    def test_plus_110(self):
        assert american_to_decimal(110) == pytest.approx(2.1)

    def test_minus_110(self):
        assert american_to_decimal(-110) == pytest.approx(1.9091, rel=1e-3)

    def test_large_underdog(self):
        # +1000 = 11.0 decimal
        assert american_to_decimal(1000) == pytest.approx(11.0)

    def test_large_favorite(self):
        # -1000 = 1.1 decimal
        assert american_to_decimal(-1000) == pytest.approx(1.1)


class TestKellyCriterionEdgeCases:
    def test_exactly_break_even(self):
        # Implied prob of -110 is 52.38%; at exactly that probability Kelly ≈ 0.
        # We use a value just above break-even to confirm the fraction is positive.
        kf = kelly_criterion(0.5240, -110)
        assert kf >= 0

    def test_tiny_edge(self):
        # Very small edge should return small positive fraction
        kf = kelly_criterion(0.5050, -100)
        assert 0 < kf < 0.05

    def test_large_edge(self):
        # 70% chance at +200 is a massive edge
        kf = kelly_criterion(0.70, 200)
        assert kf > 0.3


class TestClosingLineValueEdgeCases:
    def test_same_line(self):
        # No movement = 0 CLV
        clv = closing_line_value(-110, -110)
        assert clv == pytest.approx(0.0, abs=0.01)

    def test_line_moved_in_your_favour_underdog(self):
        # Bet +200, closed +150 — closing line is shorter, you got better price
        clv = closing_line_value(200, 150)
        assert clv > 0

    def test_line_moved_against_you_favourite(self):
        # Bet -200, closed -150 — market shortened, you got worse price
        clv = closing_line_value(-200, -150)
        assert clv < 0


class TestNoVigProbabilityEdgeCases:
    def test_heavy_favourite(self):
        p_a, p_b = no_vig_probability(-400, 320)
        assert p_a + p_b == pytest.approx(1.0, rel=1e-4)
        assert p_a > 0.75

    def test_symmetry(self):
        # Swapping sides should swap probabilities
        p_a1, p_b1 = no_vig_probability(-150, 130)
        p_a2, p_b2 = no_vig_probability(130, -150)
        assert p_a1 == pytest.approx(p_b2, rel=1e-4)
        assert p_b1 == pytest.approx(p_a2, rel=1e-4)


class TestParlayOddsEdgeCases:
    def test_three_legs(self):
        # Three -110 legs: each decimal = 1.9091, combined = 6.975 ≈ +598
        result = parlay_odds([-110, -110, -110])
        assert result > 500

    def test_mixed_legs(self):
        # -200 (1.5) * +300 (4.0) = 6.0 decimal = +500
        result = parlay_odds([-200, 300])
        assert result == pytest.approx(500, abs=5)


class TestFindBestLineEdgeCases:
    def test_all_same(self):
        books = {"DK": -110, "FD": -110, "MGM": -110}
        book, odds = find_best_line(books)
        assert odds == -110

    def test_single_book(self):
        books = {"DK": 150}
        book, odds = find_best_line(books)
        assert book == "DK"
        assert odds == 150

    def test_lay_side(self):
        # For laying, want lowest odds (least payout to other side)
        books = {"DK": -170, "FD": -175, "MGM": -165}
        book, odds = find_best_line(books, side="lay")
        assert book == "FD"
        assert odds == -175

@pytest.mark.parametrize("config, expected", [
    ('{"api_key": "demo"}', "demo"),
    ('{"api_key": 42}', None),
    ('[]', None),
])
def test_config_api_key_requires_a_string(tmp_path, monkeypatch, config, expected):
    from odds_cli import main

    path = tmp_path / "config.json"
    path.write_text(config)
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    monkeypatch.setattr(main, "CONFIG_FILE", path)
    assert main.get_api_key() == expected
