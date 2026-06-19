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


def test_synthesis_pt_a08_elbow_carrying_angle():

    findings = {"PT-A08_left": "severe"}

    result = generate_synthesis(findings)

    assert "Forearm Flexors" in result["hypertonic"]
    assert "Forearm Extensors" in result["inhibited"]


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
