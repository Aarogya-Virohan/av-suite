import requests

def test_post_apiv1authlogin_with_invalid_credentials():
    base_url = "http://localhost:8000"
    url = f"{base_url}/api/v1/auth/login"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "email": "invaliduser@example.com",
        "password": "wrongpassword123"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
    except requests.RequestException as e:
        assert False, f"Request failed with exception: {e}"

    assert response.status_code == 401, f"Expected status code 401 but got {response.status_code}"

    try:
        response_json = response.json()
    except ValueError:
        assert False, "Response is not a valid JSON"

    # The API should return an error message indicating unauthorized error
    # We expect a key like "detail" or "error" with a message containing 'Unauthorized' or similar
    error_message = response_json.get("detail") or response_json.get("error") or ""
    assert error_message, "Response JSON does not contain an error message"
    assert "unauthorized" in error_message.lower() or "invalid" in error_message.lower() or "credentials" in error_message.lower() or "incorrect" in error_message.lower(), \
        f"Unexpected error message: {error_message}"

test_post_apiv1authlogin_with_invalid_credentials()
