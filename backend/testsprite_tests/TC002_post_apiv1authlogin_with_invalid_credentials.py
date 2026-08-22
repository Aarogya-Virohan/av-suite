import requests

def test_post_apiv1authlogin_with_invalid_credentials():
    base_url = "http://localhost:8000"
    url = f"{base_url}/api/v1/auth/login"
    # Use valid email but incorrect password to test invalid login
    payload = {
        "email": "admin1@clinic.com",
        "password": "wrongpassword"
    }
    headers = {
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 401, f"Expected 401 Unauthorized but got {response.status_code}"
    try:
        json_response = response.json()
    except ValueError:
        assert False, "Response is not a valid JSON"

    # Check presence of error message or detail explaining unauthorized access
    error_keys = ["detail", "error", "message"]
    assert any(key in json_response for key in error_keys), "Response JSON should contain an error message"

test_post_apiv1authlogin_with_invalid_credentials()