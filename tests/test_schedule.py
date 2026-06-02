"""Unit tests for the dose schedule logic (is_due / doses_per_week).

const.py has no Home Assistant imports, so we load it in isolation (without
triggering the integration package __init__, which does import HA). That keeps
these tests fast and dependency-free, needing only pytest.
"""
import importlib.util
from datetime import date
from pathlib import Path

_CONST = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "medication_reminder"
    / "const.py"
)
_spec = importlib.util.spec_from_file_location("med_const", _CONST)
const = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(const)

is_due = const.is_due
doses_per_week = const.doses_per_week
WEEKDAYS = const.WEEKDAYS

# A known Monday, for weekday tests that don't hardcode the mapping.
MON = date(2026, 6, 1)


# --- Weekday schedule (default, backward compatible) -----------------------

def test_weekday_due_when_listed():
    wd = WEEKDAYS[MON.weekday()]
    assert is_due({"days": [wd]}, MON) is True


def test_weekday_not_due_when_only_other_day():
    other = WEEKDAYS[(MON.weekday() + 3) % 7]
    assert is_due({"days": [other]}, MON) is False


def test_weekday_missing_days_is_daily():
    assert is_due({}, MON) is True


def test_weekday_full_week_is_daily():
    assert is_due({"days": WEEKDAYS}, MON) is True


# --- Interval (every N days) -----------------------------------------------

INTERVAL = {"schedule_type": "interval", "interval_days": 2, "anchor_date": "2026-06-01"}


def test_interval_due_on_anchor():
    assert is_due(INTERVAL, date(2026, 6, 1)) is True


def test_interval_not_due_anchor_plus_1():
    assert is_due(INTERVAL, date(2026, 6, 2)) is False


def test_interval_due_anchor_plus_2():
    assert is_due(INTERVAL, date(2026, 6, 3)) is True


def test_interval_due_anchor_plus_4():
    assert is_due(INTERVAL, date(2026, 6, 5)) is True


def test_interval_not_due_before_anchor():
    assert is_due(INTERVAL, date(2026, 5, 31)) is False


def test_interval_n1_is_daily():
    one = {"schedule_type": "interval", "interval_days": 1, "anchor_date": "2026-06-01"}
    assert is_due(one, date(2026, 6, 9)) is True


def test_interval_no_anchor_is_deterministic():
    na = {"schedule_type": "interval", "interval_days": 3}
    d = MON
    while d.toordinal() % 3 != 0:
        d = date.fromordinal(d.toordinal() + 1)
    assert is_due(na, d) is True
    assert is_due(na, date.fromordinal(d.toordinal() + 1)) is False


def test_interval_zero_is_safe():
    # invalid 0 falls back to the default interval, never divides by zero
    z = {"schedule_type": "interval", "interval_days": 0, "anchor_date": "2026-06-01"}
    assert is_due(z, date(2026, 6, 1)) is True


# --- On/off cycle (e.g. 21 on / 7 off) -------------------------------------

CYCLE = {
    "schedule_type": "cycle",
    "cycle_on": 21,
    "cycle_off": 7,
    "anchor_date": "2026-06-01",
}


def test_cycle_due_on_anchor():
    assert is_due(CYCLE, date(2026, 6, 1)) is True


def test_cycle_due_last_on_day():
    assert is_due(CYCLE, date(2026, 6, 21)) is True  # offset 20, still in the 21 on


def test_cycle_not_due_first_off_day():
    assert is_due(CYCLE, date(2026, 6, 22)) is False  # offset 21, into the 7 off


def test_cycle_not_due_last_off_day():
    assert is_due(CYCLE, date(2026, 6, 28)) is False  # offset 27


def test_cycle_due_next_cycle_start():
    assert is_due(CYCLE, date(2026, 6, 29)) is True  # offset 28, wraps to on


def test_cycle_not_due_before_anchor():
    assert is_due(CYCLE, date(2026, 5, 31)) is False


def test_cycle_short_2on_1off():
    c = {"schedule_type": "cycle", "cycle_on": 2, "cycle_off": 1, "anchor_date": "2026-06-01"}
    assert is_due(c, date(2026, 6, 1)) is True   # offset 0
    assert is_due(c, date(2026, 6, 2)) is True   # offset 1
    assert is_due(c, date(2026, 6, 3)) is False  # offset 2 (off)
    assert is_due(c, date(2026, 6, 4)) is True   # offset 3 wraps to on


def test_dpw_cycle_21_7():
    assert abs(doses_per_week(CYCLE) - (7.0 * 21 / 28)) < 1e-9  # 5.25


# --- doses_per_week (run-out estimate cadence) -----------------------------

def test_dpw_weekdays_is_len_days():
    assert doses_per_week({"days": ["mon", "wed", "fri"]}) == 3.0


def test_dpw_daily_is_seven():
    assert doses_per_week({}) == 7.0


def test_dpw_interval_every_two():
    assert abs(doses_per_week({"schedule_type": "interval", "interval_days": 2}) - 3.5) < 1e-9


def test_dpw_interval_every_seven():
    assert abs(doses_per_week({"schedule_type": "interval", "interval_days": 7}) - 1.0) < 1e-9
