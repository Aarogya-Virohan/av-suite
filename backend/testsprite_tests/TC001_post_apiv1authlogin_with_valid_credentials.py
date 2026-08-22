import requests

def test_post_apiv1authlogin_with_valid_credentials():
    base_url = "http://localhost:8000"
    login_url = f"{base_url}/api/v1/auth/login"
    payload = {
        "email": "admin1@clinic.com",
        "password": "password123"
    }
    headers = {
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(login_url, json=payload, headers=headers, timeout=30)
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        json_response = response.json()
        assert "access_token" in json_response, "Response JSON does not contain access_token"
        assert isinstance(json_response["access_token"], str) and len(json_response["access_token"]) > 0, "access_token is invalid"
        assert "token_type" in json_response, "Response JSON does not contain token_type"
        assert json_response["token_type"].lower() == "bearer", f"Expected token_type 'bearer', got '{json_response['token_type']}'"
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

test_post_apiv1authlogin_with_valid_credentials()