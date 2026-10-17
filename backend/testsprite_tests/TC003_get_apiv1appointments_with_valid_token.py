import requests

BASE_URL = "http://localhost:8000"
LOGIN_ENDPOINT = "/api/v1/auth/login"
APPOINTMENTS_ENDPOINT = "/api/v1/appointments"
TIMEOUT = 30

def test_get_apiv1appointments_with_valid_token():
    # Valid user credentials for login - should be replaced with real valid credentials for actual testing
    login_payload = {
        "email": "testuser@example.com",
        "password": "TestPassword123!"
    }
    try:
        # Step 1: Login to get JWT token
        login_response = requests.post(
            BASE_URL + LOGIN_ENDPOINT,
            json=login_payload,
            timeout=TIMEOUT
        )
        assert login_response.status_code == 200, f"Login failed with status {login_response.status_code}"
        login_data = login_response.json()
        assert "access_token" in login_data and "token_type" in login_data, "Missing token in login response"
        token_type = login_data["token_type"]
        access_token = login_data["access_token"]
        assert token_type.lower() == "bearer", f"Unexpected token_type: {token_type}"

        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        # Step 2: Call GET /api/v1/appointments with valid token
        appointments_response = requests.get(
            BASE_URL + APPOINTMENTS_ENDPOINT,
            headers=headers,
            timeout=TIMEOUT
        )

        # Validate response status code and JSON data presence
        assert appointments_response.status_code == 200, f"Expected 200 OK, got {appointments_response.status_code}"
        appointments_data = appointments_response.json()
        assert isinstance(appointments_data, list) or isinstance(appointments_data, dict), "Appointments response is not JSON list/dict"

    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

test_get_apiv1appointments_with_valid_token()