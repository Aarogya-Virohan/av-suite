from app.services.posture.synthesizer import generate_synthesis


def test_synthesis_single_part_key():

    # Existing pattern: keys with no underscore, e.g. "PT-L01".
    findings = {"PT-L01": "moderate"}

    result = generate_synthesis(findings)

    assert "Upper Trapezius" in result["hypertonic"]
    assert "Deep Neck Flexors" in result["inhibited"]
    assert any(ex["exercise"] == "Chin Tucks" for ex in result["correctiveProtocol"])


def test_synthesis_bilateral_key():

    # Existing pattern: keys with one underscore (side suffix), e.g. "PT-A05_left".
    findings = {"PT-A05_left": "moderate"}

    result = generate_synthesis(findings)

    assert "Gluteus Medius" in result["inhibited"]
    assert any(ex["exercise"] == "Clamshells" for ex in result["correctiveProtocol"])


def test_synthesis_pt_l06_knee_hyperextension():

    findings = {"PT-L06": "moderate"}

    result = generate_synthesis(findings)

    assert "Gastrocnemius" in result["hypertonic"]
    assert "Quadriceps" in result["inhibited"]
    assert any(
        ex["exercise"] == "Terminal Knee Extension Control"
        for ex in result["correctiveProtocol"]
    )


def test_withdrawn_parameters_trigger_nothing():

    # PT-P03 and PT-P05 were withdrawn on 1 October 2026, PT-A08 and
    # PT-P04 on 2 October. Their calculations and bands are deliberately
    # left in the source, so the only thing stopping them reaching a
    # patient is that nothing calls them and nothing maps them. This
    # pins the second half: if a mapping is ever added back without the
    # parameter being deliberately reinstated, this fails.

    for param in ("PT-A08_left", "PT-A08_right", "PT-P03_left", "PT-P04", "PT-P05"):

        result = generate_synthesis({param: "severe"})

        assert result["hypertonic"] == [], f"{param} still maps hypertonic muscles"
        assert result["inhibited"] == [], f"{param} still maps inhibited muscles"
        assert result["correctiveProtocol"] == [], f"{param} still maps an exercise"


def test_synthesis_three_part_key_does_not_crash():

    # "<param>_<subtype>_<side>" style keys (3 parts) derive
    # base_param_id = "<param>_<subtype>". No current rule matches this
    # made-up id, so it should simply find nothing rather than crash.
    result = generate_synthesis({"PT-XX_low_left": "moderate"})

    assert result["hypertonic"] == []
    assert result["inhibited"] == []
    assert result["correctiveProtocol"] == []


def test_synthesis_ignores_none_and_mild_severities():

    findings = {
        "PT-L06": "none",
        "PT-A08_left": "mild",
    }

    result = generate_synthesis(findings)

    assert result["hypertonic"] == []
    assert result["inhibited"] == []
    assert result["correctiveProtocol"] == []
