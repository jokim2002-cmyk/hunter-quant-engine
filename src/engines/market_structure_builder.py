from typing import Any, List
import inspect

from src.models.market_structure import MarketStructurePoint


class MarketStructureBuilder:
    """
    Converts swing points into market structure points.

    HIGH swings become:
    - HH = Higher High
    - LH = Lower High

    LOW swings become:
    - HL = Higher Low
    - LL = Lower Low
    """

    def build(self, swing_points: List[Any]) -> List[MarketStructurePoint]:
        market_structure_points = []

        last_high_price = None
        last_low_price = None

        for swing in swing_points:
            swing_type = self._get_swing_type(swing)
            price = self._get_price(swing)

            if swing_type == "HIGH":
                structure_type = "HH" if last_high_price is None or price > last_high_price else "LH"
                last_high_price = price

            elif swing_type == "LOW":
                structure_type = "LL" if last_low_price is None or price < last_low_price else "HL"
                last_low_price = price

            else:
                raise ValueError(f"Invalid swing type: {swing_type}")

            market_structure_points.append(
                self._create_market_structure_point(
                    swing=swing,
                    structure_type=structure_type,
                    price=price,
                    swing_type=swing_type,
                )
            )

        return market_structure_points

    def _get_swing_type(self, swing: Any) -> str:
        for attr in ("swing_type", "type", "point_type"):
            if hasattr(swing, attr):
                return str(getattr(swing, attr)).upper()

        raise AttributeError("Swing point must have swing_type, type, or point_type")

    def _get_price(self, swing: Any) -> float:
        for attr in ("price", "value"):
            if hasattr(swing, attr):
                return float(getattr(swing, attr))

        raise AttributeError("Swing point must have price or value")

    def _create_market_structure_point(
        self,
        swing: Any,
        structure_type: str,
        price: float,
        swing_type: str,
    ) -> MarketStructurePoint:
        signature = inspect.signature(MarketStructurePoint)
        allowed_fields = signature.parameters.keys()

        data = {
            "index": getattr(swing, "index", None),
            "timestamp": getattr(swing, "timestamp", None),
            "price": price,
            "structure_type": structure_type,
            "swing_type": swing_type,
            "swing_point": swing,
        }

        filtered_data = {
            key: value
            for key, value in data.items()
            if key in allowed_fields and value is not None
        }

        return MarketStructurePoint(**filtered_data)
