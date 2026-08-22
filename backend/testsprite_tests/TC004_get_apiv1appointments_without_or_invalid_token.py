import requests

BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/api/v1/auth/login"
APPOINTMENTS_URL = f"{BASE_URL}/api/v1/appointments"

def test_get_apiv1appointments_without_or_invalid_token():
    # Test without token
    response_no_token = requests.get(APPOINTMENTS_URL, timeout=30)
    assert response_no_token.status_code == 401, f"Expected 401, got {response_no_token.status_code}"
    resp_json = response_no_token.json()
    assert "detail" in resp_json, "Response JSON should contain 'detail' key"
    
    # Test with invalid token
    invalid_headers = {"Authorization": "Bearer invalidtoken123"}
    response_invalid_token = requests.get(APPOINTMENTS_URL, headers=invalid_headers, timeout=30)
    assert response_invalid_token.status_code == 401, f"Expected 401, got {response_invalid_token.status_code}"
    resp_json = response_invalid_token.json()
    assert "detail" in resp_json, "Response JSON should contain 'detail' key"

test_get_apiv1appointments_without_or_invalid_token()