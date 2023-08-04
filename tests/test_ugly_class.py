"""tests for ugly_lib Ugly class"""

import pytest
from ugly_lib import Ugly

def test_ValidateIP_not_string_exception():
    with pytest.raises(ValueError) as e:
        arg=4444444
        Ugly.ValidateIP(arg)

    assert 'ip not a string' in str(e.value)

def test_ValidateIP_not_4_parts_exception():
    with pytest.raises(ValueError) as e:
        arg='1.1.1.'
        Ugly.ValidateIP(arg)

    assert 'ip not a dotted quad' in str(e.value)

def test_ValidateIP_not_all_ints_exception():
    with pytest.raises(ValueError) as e:
        arg='1.1.1.a'
        Ugly.ValidateIP(arg)

    assert 'ip dotted-quad components not all integers' in str(e.value)

def test_ValidateIP_quad_lt_zero_exception():
    with pytest.raises(ValueError) as e:
        arg='1.1.1.-1'
        Ugly.ValidateIP(arg)

    assert 'ip dotted-quad component not between 0 and 255' in str(e.value)

def test_ValidateIP_quad_gt_255_exception():
    with pytest.raises(ValueError) as e:
        arg='1.1.1.256'
        Ugly.ValidateIP(arg)

    assert 'ip dotted-quad component not between 0 and 255' in str(e.value)

def test_ValidateIP_valid():
    arg='1.1.1.1'
    value = Ugly.ValidateIP(arg)

    assert value is None
