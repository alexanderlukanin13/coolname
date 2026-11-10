"""A non-positive --number must be rejected, not silently accepted."""

import pytest

from coolname.__main__ import parse_args


def test_number_zero_rejected():
    with pytest.raises(SystemExit) as exc:
        parse_args(["-n", "0"])
    assert exc.value.code == 2


def test_number_negative_rejected():
    with pytest.raises(SystemExit) as exc:
        parse_args(["-n", "-5"])
    assert exc.value.code == 2


def test_number_positive_accepted():
    args = parse_args(["-n", "3"])
    assert args.number == 3
