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


def test_synthesis_pt_l08_low_and_high_two_underscore_keys():

    # New pattern: keys with two underscores ("PT-L08_low_left" /
    # "PT-L08_high_right") — base param id is everything except the
    # trailing side suffix.
    low = generate_synthesis({"PT-L08_low_left": "moderate"})

    assert "Tibialis Posterior" in low["inhibited"]
    assert any(ex["exercise"] == "Short Foot Exercise" for ex in low["correctiveProtocol"])

    high = generate_synthesis({"PT-L08_high_right": "moderate"})

    assert "Peroneus Longus" in high["hypertonic"]
    assert any(
        ex["exercise"] == "Calf Stretching & Ankle Mobility"
        for ex in high["correctiveProtocol"]
    )


def test_synthesis_ignores_none_and_mild_severities():

    findings = {
        "PT-L06": "none",
        "PT-A08_left": "mild",
        "PT-L08_low_left": "insufficient_data",
    }

    result = generate_synthesis(findings)

    assert result["hypertonic"] == []
    assert result["inhibited"] == []
    assert result["correctiveProtocol"] == []
