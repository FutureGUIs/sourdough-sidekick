"""Sidekick field metadata and value conversion, independent of Home Assistant."""
from dataclasses import dataclass
from math import isfinite
from typing import Any


@dataclass(frozen=True)
class SourdoughField:
    key: str
    uid: str
    label: str
    kind: str = "number"
    enum_prefix: str = ""


# Retain the upstream unique-ID suffixes for the original seven fields.
FIELDS = (
    SourdoughField("state", "sourdough_state", "Starter Status", "enum", "cloud.smarthq.type.runstatus."),
    SourdoughField("mode", "sourdough_mode", "Starter Mode", "enum", "cloud.smarthq.type.mode."),
    SourdoughField("goalTimeHours", "sourdough_goal_h", "Goal Hour"),
    SourdoughField("goalTimeMinutes", "sourdough_goal_m", "Goal Minute"),
    SourdoughField("flourRatio", "sourdough_flour", "Flour Ratio"),
    SourdoughField("waterRatio", "sourdough_water", "Water Ratio"),
    SourdoughField("starterRatio", "sourdough_starter", "Starter Ratio"),
    SourdoughField("goalDay", "sourdough_goal_day", "Goal Day", "enum", "cloud.smarthq.type.weekday."),
    SourdoughField("goalAmount", "sourdough_goal_amount", "Goal Amount", "mass"),
    SourdoughField("flourMass", "sourdough_flour_mass", "Flour Amount", "mass"),
    SourdoughField("waterMass", "sourdough_water_mass", "Water Amount", "mass"),
    SourdoughField("starterMass", "sourdough_starter_mass", "Starter Amount", "mass"),
    SourdoughField("feedingFrequency", "sourdough_feeding_frequency", "Feeding Frequency"),
)


def field_unit(field: SourdoughField, config: dict[str, Any]) -> str | None:
    """Use declared mass units; leave unknown units and ratios unlabelled."""
    if field.kind != "mass":
        return None
    return {
        "cloud.smarthq.type.weightunits.grams": "g",
        "cloud.smarthq.type.weightunits.ounces": "oz",
        "cloud.smarthq.type.weightunits.pounds": "lb",
    }.get(config.get("weightUnits"))


def field_value(field: SourdoughField, state: dict[str, Any]) -> str | int | float | None:
    """Preserve numeric readings and readable enums without inventing defaults."""
    value = state.get(field.key)
    if field.kind == "enum":
        if not isinstance(value, str) or not value:
            return None
        return value.removeprefix(field.enum_prefix)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if isfinite(value) else None


def is_crock_presence(service: dict[str, Any]) -> bool:
    """Match the documented crock service tuple without affecting other toggles."""
    return (
        service.get("serviceType") == "cloud.smarthq.service.toggle"
        and service.get("domainType") == "cloud.smarthq.domain.presence"
        and service.get("serviceDeviceType") == "cloud.smarthq.device.crock"
    )


def crock_present(state: dict[str, Any]) -> bool | None:
    """Unknown or disabled state must not be mistaken for an absent crock."""
    if state.get("disabled") or not isinstance(state.get("on"), bool):
        return None
    return state["on"]
