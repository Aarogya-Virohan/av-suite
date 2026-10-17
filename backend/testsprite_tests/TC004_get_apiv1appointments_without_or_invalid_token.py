import requests

BASE_URL = "http://localhost:8000"

def test_get_appointments_without_or_invalid_token():
    url = f"{BASE_URL}/api/v1/appointments"

    # Case 1: Without token
    response_no_token = requests.get(url, timeout=30)
    try:
        assert response_no_token.status_code == 401, f"Expected 401 Unauthorized, got {response_no_token.status_code}"
    except AssertionError:
        print("Response JSON (no token):", response_no_token.text)
        raise

    # Case 2: With invalid token
    headers_invalid_token = {
        "Authorization": "Bearer invalidtoken123"
    }
    response_invalid_token = requests.get(url, headers=headers_invalid_token, timeout=30)
    try:
        assert response_invalid_token.status_code == 401, f"Expected 401 Unauthorized, got {response_invalid_token.status_code}"
    except AssertionError:
        print("Response JSON (invalid token):", response_invalid_token.text)
        raise

test_get_appointments_without_or_invalid_token()