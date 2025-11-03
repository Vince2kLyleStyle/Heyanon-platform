import os
import sys
import math

# adjust path to import module when running tests from repository root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from copy_executor import apply_symbol_rounding


def test_btc_rounding():
    qty, min_notional = apply_symbol_rounding('BTC-PERP', 0.00123456, 60000)
    # stepSize 0.0001 -> floor to nearest 0.0001 => 0.0012
    assert abs(qty - 0.0012) < 1e-12
    assert min_notional == 1.0


def test_eth_rounding():
    qty, min_notional = apply_symbol_rounding('ETH-PERP', 0.0123456, 1800)
    # stepSize 0.001 -> floor to nearest 0.001 => 0.012
    assert abs(qty - 0.012) < 1e-12
    assert min_notional == 1.0


def test_fallback_rounding():
    qty, mn = apply_symbol_rounding('UNKNOWN', 0.000000123456, 100)
    # fallback uses 8-decimals floor
    assert abs(qty - math.floor(0.000000123456 * 1e8) / 1e8) < 1e-18
    assert mn == 0.0


def test_sol_rounding():
    qty, mn = apply_symbol_rounding('SOL-PERP', 0.12345, 20)
    # stepSize 0.01 -> floor to nearest 0.01 -> 0.12
    assert abs(qty - 0.12) < 1e-12
    assert mn == 5


def test_xrp_rounding():
    qty, mn = apply_symbol_rounding('XRP-PERP', 123.45, 0.5)
    # stepSize 1 -> floor to nearest 1 -> 123
    assert abs(qty - 123) < 1e-12
    assert mn == 5
