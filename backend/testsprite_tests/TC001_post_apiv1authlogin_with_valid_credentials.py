import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_post_apiv1authlogin_with_valid_credentials():
    url = f"{BASE_URL}/api/v1/auth/login"
    headers = {
        "Content-Type": "application/json"
    }
    # Substitute with valid credentials known to exist in the system
    payload = {
        "email": "validuser@example.com",
        "password": "ValidPassword123!"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    try:
        resp_json = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"

    assert "access_token" in resp_json, "Response JSON missing 'access_token'"
    assert isinstance(resp_json["access_token"], str) and len(resp_json["access_token"]) > 0, \
        "'access_token' should be a non-empty string"
    assert "token_type" in resp_json, "Response JSON missing 'token_type'"
    assert resp_json["token_type"].lower() == "bearer", f"Expected token_type to be 'bearer', got '{resp_json['token_type']}'"

test_post_apiv1authlogin_with_valid_credentials()