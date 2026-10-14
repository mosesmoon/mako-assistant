"""Per-game MAKO Renderer settings: what each profile field accepts.

Ranges and choices were checked against ``mako-cli validate`` (MAKO Renderer
standalone 4.0); labels follow MAKO UI. This module has no Qt dependency so
the service layer and the tests can use it.

Every field maps to one key of a ``[[profile]]`` table in ``conf.toml``,
except the "ratio" fields: MAKO UI shows "0x" in the multiplier lists, which
is not a multiplier value but ``frame_generation_enabled = false`` (a live
pause). Picking 2x–5x writes the multiplier and resumes generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# Fallbacks for keys a profile does not have yet. The default profile `mako`
# is consulted first (see `effective_values`), so these only matter when both
# lack a key.
DEFAULTS: dict[str, Any] = {
    "frame_generation_provisioned": True,
    "frame_generation_enabled": True,
    "adaptive": False,
    "multiplier": 2,
    "adaptive_max_multiplier": 3,
    "target_fps": 90,
    "adaptive_auto_base_fps_cap": False,
    "adaptive_fractional_real_frame_priority": "auto",
    "adaptive_stable_cadence": True,
    "dynamic_cadence_recovery": False,
    "dynamic_cadence_probe_interval_seconds": 2.0,
    "flow_scale": 0.85,
    "performance_mode": False,
    "ultra_performance": False,
    "base_fps_cap": 0,
    "gamescope_vrr_mode": "follow-steam",
    "frame_generation_refresh_threshold": 0,
    "scaling_enabled": False,
    "scaling_method": "ls1",
    "scaling_factor": 1.5,
    "scaling_sharpness": 0.8,
    "scaling_supersampling": False,
    "swapchain_image_count_compatibility": False,
}

Values = dict[str, Any]


@dataclass(frozen=True)
class Field:
    key: str
    kind: str                    # toggle | segment | ratio | slider | number
    label: str                   # i18n key
    desc: str = ""               # i18n key
    options: tuple = ()          # segment: ((value, i18n key), ...)
    minimum: float = 0
    maximum: float = 0
    step: float = 1
    unit: str = ""               # percent | x | fps | s
    off_at_zero: bool = False    # number: 0 means "Off"
    restart: bool = False        # takes effect on the next game launch
    visible: Optional[Callable[[Values], bool]] = None
    enabled: Optional[Callable[[Values], bool]] = None


@dataclass(frozen=True)
class Section:
    key: str                     # i18n key of the title
    fields: tuple = field(default_factory=tuple)
    icon: str = ""
    visible: Optional[Callable[[Values], bool]] = None


def _fg_on(v: Values) -> bool:
    return bool(v.get("frame_generation_provisioned", True))


SECTIONS: tuple[Section, ...] = (
    Section("set_sec_fg", icon="spark", fields=(
        Field("frame_generation_provisioned", "toggle", "set_provisioned", "set_provisioned_desc",
              restart=True),
        Field("adaptive", "segment", "set_mode", "set_mode_desc",
              options=((False, "set_mode_fixed"), (True, "set_mode_adaptive")), enabled=_fg_on),
        Field("multiplier", "ratio", "set_multiplier", "set_multiplier_desc",
              minimum=2, maximum=5, unit="x", enabled=_fg_on,
              visible=lambda v: not v.get("adaptive")),
        Field("adaptive_max_multiplier", "ratio", "set_max_multiplier", "set_max_multiplier_desc",
              minimum=2, maximum=5, unit="x", enabled=_fg_on,
              visible=lambda v: bool(v.get("adaptive"))),
        Field("flow_scale", "slider", "set_flow", "set_flow_desc",
              minimum=0.25, maximum=1.0, step=0.05, unit="percent", enabled=_fg_on),
        Field("performance_mode", "toggle", "set_lighter", "set_lighter_desc",
              enabled=lambda v: _fg_on(v) and not v.get("ultra_performance")),
        Field("ultra_performance", "toggle", "set_ultra", "set_ultra_desc", restart=True,
              enabled=_fg_on),
    )),
    Section("set_sec_adaptive", icon="gauge", visible=lambda v: bool(v.get("adaptive")), fields=(
        Field("target_fps", "number", "set_target_fps", "set_target_fps_desc",
              minimum=10, maximum=1000, unit="fps"),
        Field("adaptive_auto_base_fps_cap", "toggle", "set_steady_cap", "set_steady_cap_desc"),
        Field("adaptive_fractional_real_frame_priority", "segment", "set_priority",
              "set_priority_desc",
              options=(("auto", "set_auto"), ("low", "set_low"), ("medium", "set_medium"),
                       ("high", "set_high"), ("very-high", "set_very_high")),
              enabled=lambda v: not v.get("adaptive_auto_base_fps_cap")),
        Field("adaptive_stable_cadence", "toggle", "set_smooth_cadence", "set_smooth_cadence_desc"),
        Field("dynamic_cadence_recovery", "toggle", "set_dyn_cadence", "set_dyn_cadence_desc"),
        Field("dynamic_cadence_probe_interval_seconds", "slider", "set_probe", "set_probe_desc",
              minimum=0.1, maximum=3.0, step=0.1, unit="s",
              enabled=lambda v: bool(v.get("dynamic_cadence_recovery"))),
    )),
    Section("set_sec_pacing", icon="pulse", fields=(
        Field("base_fps_cap", "number", "set_base_cap", "set_base_cap_desc",
              minimum=0, maximum=1000, unit="fps", off_at_zero=True),
        Field("gamescope_vrr_mode", "segment", "set_vrr", "set_vrr_desc",
              options=(("follow-steam", "set_vrr_follow"), ("on", "set_on"), ("off", "set_off"))),
        Field("frame_generation_refresh_threshold", "number", "set_refresh_guard",
              "set_refresh_guard_desc", minimum=0, maximum=1000, unit="fps", off_at_zero=True),
    )),
    Section("set_sec_scaling", icon="expand", fields=(
        Field("scaling_enabled", "toggle", "set_scaling", "set_scaling_desc", restart=True),
        Field("scaling_method", "segment", "set_scaling_method", "set_scaling_method_desc",
              options=(("native", "set_method_native"), ("mako", "set_method_mako"),
                       ("ls1", "set_method_ls1"), ("ls1-performance", "set_method_ls1_perf")),
              enabled=lambda v: bool(v.get("scaling_enabled"))),
        Field("scaling_factor", "slider", "set_scale_factor", "set_scale_factor_desc",
              minimum=1.0, maximum=2.0, step=0.05, unit="x",
              enabled=lambda v: bool(v.get("scaling_enabled"))),
        Field("scaling_sharpness", "slider", "set_sharpness", "set_sharpness_desc",
              minimum=0.0, maximum=1.0, step=0.05, unit="percent",
              enabled=lambda v: bool(v.get("scaling_enabled"))
              and v.get("scaling_method") != "native"),
        Field("scaling_supersampling", "toggle", "set_supersampling", "set_supersampling_desc",
              enabled=lambda v: bool(v.get("scaling_enabled"))),
    )),
    Section("set_sec_compat", icon="shield", fields=(
        Field("swapchain_image_count_compatibility", "toggle", "set_swapchain",
              "set_swapchain_desc", restart=True),
    )),
)

FIELDS: dict[str, Field] = {f.key: f for s in SECTIONS for f in s.fields}
# Keys this module may write: every field, plus the live pause behind "0x".
WRITABLE = frozenset(FIELDS) | {"frame_generation_enabled"}


def effective_values(profile: Values, default_profile: Optional[Values] = None) -> Values:
    """The values the panel shows: the profile's own, else the default profile's, else ours."""
    base = dict(DEFAULTS)
    if default_profile:
        base.update({k: v for k, v in default_profile.items() if k in DEFAULTS})
    base.update({k: v for k, v in profile.items() if k in DEFAULTS})
    return base


def ratio_value(values: Values, key: str) -> int:
    """What a ratio field shows: 0 while generation is paused, else the multiplier."""
    return 0 if not values.get("frame_generation_enabled", True) else int(values.get(key, 2))


def coerce(key: str, value: Any) -> Any:
    """Validate one value against MAKO's rules; return it in the type conf.toml expects."""
    if key == "frame_generation_enabled":
        if not isinstance(value, bool):
            raise ValueError(f"{key}: expected true or false")
        return value
    spec = FIELDS.get(key)
    if spec is None:
        raise ValueError(f"{key}: not a per-game setting")
    if spec.kind == "toggle":
        if not isinstance(value, bool):
            raise ValueError(f"{key}: expected true or false")
        return value
    if spec.kind == "segment":
        allowed = [v for v, _ in spec.options]
        if value not in allowed or isinstance(value, bool) != isinstance(allowed[0], bool):
            raise ValueError(f"{key}: expected one of {allowed}")
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key}: expected a number")
    if spec.kind in ("ratio", "number"):
        if value != int(value):
            raise ValueError(f"{key}: expected a whole number")
        value = int(value)
        if spec.off_at_zero and value == 0:
            return 0
    else:  # slider: keep MAKO's float type, rounded to the step
        decimals = 2 if spec.step < 0.1 else 1
        value = round(float(value), decimals)
    if not spec.minimum <= value <= spec.maximum:
        raise ValueError(f"{key}: must be between {spec.minimum:g} and {spec.maximum:g}")
    return value


def changes_for(key: str, value: Any) -> Values:
    """The conf.toml writes one control change needs (ratio 0 = live pause)."""
    spec = FIELDS[key]
    if spec.kind == "ratio":
        if value == 0:
            return {"frame_generation_enabled": False}
        return {key: coerce(key, value), "frame_generation_enabled": True}
    return {key: coerce(key, value)}
