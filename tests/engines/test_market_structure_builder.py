from types import SimpleNamespace

from src.engines.market_structure_builder import MarketStructureBuilder


def get_structure_type(point):
    return getattr(point, "structure_type")


def test_market_structure_builder_identifies_highs_and_lows():
    swings = [
        SimpleNamespace(index=1, price=100.0, swing_type="HIGH"),
        SimpleNamespace(index=2, price=90.0, swing_type="LOW"),
        SimpleNamespace(index=3, price=110.0, swing_type="HIGH"),
        SimpleNamespace(index=4, price=95.0, swing_type="LOW"),
        SimpleNamespace(index=5, price=105.0, swing_type="HIGH"),
        SimpleNamespace(index=6, price=85.0, swing_type="LOW"),
    ]

    builder = MarketStructureBuilder()
    result = builder.build(swings)

    assert len(result) == 6
    assert [get_structure_type(point) for point in result] == [
        "HH",
        "LL",
        "HH",
        "HL",
        "LH",
        "LL",
    ]


def test_market_structure_builder_returns_empty_list_for_no_swings():
    builder = MarketStructureBuilder()

    result = builder.build([])

    assert result == []


def test_market_structure_builder_raises_error_for_invalid_swing_type():
    swings = [
        SimpleNamespace(index=1, price=100.0, swing_type="INVALID"),
    ]

    builder = MarketStructureBuilder()

    try:
        builder.build(swings)
        assert False
    except ValueError as error:
        assert "Invalid swing type" in str(error)
