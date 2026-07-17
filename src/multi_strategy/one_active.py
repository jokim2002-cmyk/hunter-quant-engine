"""Disabled one-active-strategy guard for HQE forward-paper preparation.

This module models the single selected strategy and strategy-switch review
without activating a strategy or connecting to the canonical product runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.runtime_hook import StableRuntimeObservation
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import (
    PositionLifecycle,
    StrategyStateSnapshot,
    assert_strategy_switch_allowed,
)
from src.multi_strategy.errors import SelectionSwitchBlockedError

ONE_ACTIVE_SCHEMA_VERSION = "1.0.0"


class OneActiveStrategyError(ValueError):
    """Raised when the disabled one-active invariant is inconsistent."""


class DisabledSwitchReviewStatus(str, Enum):
    """Read-only switch classification; no status authorizes a switch."""

    SAME_SELECTION_DISABLED = "SAME_SELECTION_DISABLED"
    READY_FLAT_DISABLED = "READY_FLAT_DISABLED"
    BLOCKED_RUNTIME_ACTIVE = "BLOCKED_RUNTIME_ACTIVE"
    BLOCKED_OPEN_POSITION = "BLOCKED_OPEN_POSITION"
    BLOCKED_MIGRATION = "BLOCKED_MIGRATION"
    BLOCKED_IDENTITY = "BLOCKED_IDENTITY"


@dataclass(frozen=True)
class DisabledOneActiveStrategySet:
    """Exactly one immutable selected strategy with activation disabled."""

    selection: StrategySelectionSnapshot
    active_selection_hashes: tuple[str, ...]
    schema_version: str = ONE_ACTIVE_SCHEMA_VERSION
    one_active_strategy_enforced: bool = True
    activation_enabled: bool = False
    runtime_connected: bool = False
    runtime_cutover_authorized: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != ONE_ACTIVE_SCHEMA_VERSION:
            raise OneActiveStrategyError(
                "unsupported one-active schema version"
            )
        if len(self.active_selection_hashes) != 1:
            raise OneActiveStrategyError(
                "exactly one active selection is required"
            )
        if self.active_selection_hashes[0] != self.selection.selection_hash:
            raise OneActiveStrategyError(
                "active selection does not match selected strategy"
            )
        if not self.one_active_strategy_enforced:
            raise OneActiveStrategyError(
                "one-active strategy enforcement cannot be disabled"
            )
        if (
            self.activation_enabled
            or self.runtime_connected
            or self.runtime_cutover_authorized
        ):
            raise OneActiveStrategyError(
                "disabled one-active set cannot activate or connect runtime"
            )

    @classmethod
    def build(
        cls,
        selection: StrategySelectionSnapshot,
        active_candidates: Iterable[StrategySelectionSnapshot],
    ) -> "DisabledOneActiveStrategySet":
        candidates = tuple(active_candidates)
        return cls(
            selection=selection,
            active_selection_hashes=tuple(
                candidate.selection_hash for candidate in candidates
            ),
        )

    @property
    def set_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "strategy_id": self.selection.strategy_id,
            "strategy_version": self.selection.strategy_version,
            "selection_hash": self.selection.selection_hash,
            "active_selection_hashes": list(self.active_selection_hashes),
            "active_strategy_count": 1,
            "one_active_strategy_enforced": True,
            "activation_enabled": False,
            "runtime_connected": False,
            "runtime_cutover_authorized": False,
        }
        if include_hash:
            payload["set_hash"] = self.set_hash
        return payload


@dataclass(frozen=True)
class DisabledStrategySwitchReview:
    """Fail-closed review of a requested strategy switch."""

    status: DisabledSwitchReviewStatus
    current_selection_hash: str
    requested_selection_hash: str
    current_lifecycle: PositionLifecycle
    runtime_status: str
    blockers: tuple[str, ...]
    schema_version: str = ONE_ACTIVE_SCHEMA_VERSION
    switch_authorized: bool = False
    selection_write_authorized: bool = False
    lifecycle_write_authorized: bool = False
    runtime_control_authorized: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != ONE_ACTIVE_SCHEMA_VERSION:
            raise OneActiveStrategyError(
                "unsupported switch-review schema version"
            )
        if (
            self.switch_authorized
            or self.selection_write_authorized
            or self.lifecycle_write_authorized
            or self.runtime_control_authorized
        ):
            raise OneActiveStrategyError(
                "disabled switch review cannot authorize a switch or write"
            )
        if self.status in {
            DisabledSwitchReviewStatus.SAME_SELECTION_DISABLED,
            DisabledSwitchReviewStatus.READY_FLAT_DISABLED,
        }:
            if self.blockers:
                raise OneActiveStrategyError(
                    "non-blocked switch review cannot contain blockers"
                )
        elif not self.blockers:
            raise OneActiveStrategyError(
                "blocked switch review requires blockers"
            )

    @property
    def review_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "current_selection_hash": self.current_selection_hash,
            "requested_selection_hash": self.requested_selection_hash,
            "current_lifecycle": self.current_lifecycle.value,
            "runtime_status": self.runtime_status,
            "blockers": list(self.blockers),
            "switch_authorized": False,
            "selection_write_authorized": False,
            "lifecycle_write_authorized": False,
            "runtime_control_authorized": False,
        }
        if include_hash:
            payload["review_hash"] = self.review_hash
        return payload


def review_disabled_strategy_switch(
    *,
    current_selection: StrategySelectionSnapshot,
    requested_selection: StrategySelectionSnapshot,
    current_state: StrategyStateSnapshot,
    runtime_observation: StableRuntimeObservation,
) -> DisabledStrategySwitchReview:
    """Review a switch using existing safety invariants without applying it."""

    runtime_running = runtime_observation.runtime_status == "RUNNING"
    blockers: list[str] = []

    if current_selection.selection_hash == requested_selection.selection_hash:
        status = DisabledSwitchReviewStatus.SAME_SELECTION_DISABLED
    else:
        try:
            assert_strategy_switch_allowed(
                current_selection,
                requested_selection,
                current_state,
                runtime_running=runtime_running,
            )
        except SelectionSwitchBlockedError as exc:
            message = str(exc)
            blockers.append(message)
            lowered = message.lower()
            if "runtime" in lowered:
                status = DisabledSwitchReviewStatus.BLOCKED_RUNTIME_ACTIVE
            elif "open or held" in lowered:
                status = DisabledSwitchReviewStatus.BLOCKED_OPEN_POSITION
            elif "migration" in lowered:
                status = DisabledSwitchReviewStatus.BLOCKED_MIGRATION
            else:
                status = DisabledSwitchReviewStatus.BLOCKED_IDENTITY
        else:
            status = DisabledSwitchReviewStatus.READY_FLAT_DISABLED

    return DisabledStrategySwitchReview(
        status=status,
        current_selection_hash=current_selection.selection_hash,
        requested_selection_hash=requested_selection.selection_hash,
        current_lifecycle=current_state.lifecycle,
        runtime_status=runtime_observation.runtime_status,
        blockers=tuple(blockers),
    )
