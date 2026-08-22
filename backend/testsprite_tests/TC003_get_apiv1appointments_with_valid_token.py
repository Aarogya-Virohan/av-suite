import requests

BASE_URL = "http://localhost:8000"
LOGIN_ENDPOINT = f"{BASE_URL}/api/v1/auth/login"
APPOINTMENTS_ENDPOINT = f"{BASE_URL}/api/v1/appointments"
EMAIL = "admin1@clinic.com"
PASSWORD = "password123"
TIMEOUT = 30


def test_get_apiv1appointments_with_valid_token():
    try:
        # Authenticate to get JWT token
        login_payload = {
            "email": EMAIL,
            "password": PASSWORD
        }
        login_resp = requests.post(LOGIN_ENDPOINT, json=login_payload, timeout=TIMEOUT)
        assert login_resp.status_code == 200, f"Login failed with status {login_resp.status_code}"
        login_json = login_resp.json()
        assert "access_token" in login_json and "token_type" in login_json, "Login response missing token"
        token_type = login_json["token_type"]
        access_token = login_json["access_token"]
        assert token_type.lower() == "bearer", f"Unexpected token_type: {token_type}"

        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        # Get appointments with valid token
        resp = requests.get(APPOINTMENTS_ENDPOINT, headers=headers, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Get appointments failed with status {resp.status_code}"
        resp_json = resp.json()
        assert isinstance(resp_json, (list, dict)), "Appointments response is not JSON list or dict"

    except requests.RequestException as e:
        assert False, f"HTTP request failed: {e}"


test_get_apiv1appointments_with_valid_token()