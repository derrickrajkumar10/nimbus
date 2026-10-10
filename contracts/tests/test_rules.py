import pytest

from nimbus_contracts.common import DepthBand, RiskBand, VehicleType
from nimbus_contracts.rules import band_for_score, can_pass


@pytest.mark.parametrize("score, band", [(0, "low"), (39, "low"), (40, "watch"), (69, "watch"), (70, "likely"), (100, "likely")])
def test_score_never_reaches_flooded(score, band):
    assert band_for_score(score) == RiskBand(band)


def test_two_wheeler_stalls_above_ankle_but_ambulance_takes_knee():
    assert can_pass(VehicleType.TWO_WHEELER, DepthBand.ANKLE)
    assert not can_pass(VehicleType.TWO_WHEELER, DepthBand.KNEE)
    assert can_pass(VehicleType.AMBULANCE, DepthBand.KNEE)
    assert not can_pass(VehicleType.AMBULANCE, DepthBand.WAIST)
