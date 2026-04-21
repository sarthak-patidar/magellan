#!/usr/bin/env python
"""Manual test runner with pytest stub for momentum tests."""
import sys
import re
from contextlib import contextmanager

# Install pytest stub
class _FakePytest:
    @contextmanager
    def raises(self, exc, match=None):
        try:
            yield
        except exc as e:
            if match and not re.search(match, str(e)):
                raise AssertionError(f"Exception message '{str(e)}' did not match pattern '{match}'")
            return
        raise AssertionError(f"Expected {exc.__name__} but nothing was raised")

sys.modules['pytest'] = _FakePytest()

# Now import the test module
from tests.test_momentum import (
    test_strong_uptrend_gives_positive_composite,
    test_downtrend_is_penalized,
    test_insufficient_history_raises,
)

def run_tests():
    tests = [
        ("test_strong_uptrend_gives_positive_composite", test_strong_uptrend_gives_positive_composite),
        ("test_downtrend_is_penalized", test_downtrend_is_penalized),
        ("test_insufficient_history_raises", test_insufficient_history_raises),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            test_func()
            print(f"✓ {test_name} PASSED")
            passed += 1
        except Exception as e:
            print(f"✗ {test_name} FAILED")
            print(f"  Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
