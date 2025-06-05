import requests,json
from pathlib import Path

def load_config(config_file=Path("config.json").resolve()):
    """Loads configuration values from a JSON file."""
    
    with open(config_file, "r") as file:
        return json.load(file)

def generate_oauth_token(config):
    """
    Generates an OAuth token using the provided API key.

    Parameters:
        config (dict): Configuration dictionary with IAM URL, API key, and tenant name.

    Returns:
        str: The OAuth token if successful, or an error message if not.
    """
    url = f"{config['iam_url']}{config['tenant_name']}/protocol/openid-connect/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": "ast-app",
        "refresh_token": config["api_key"]
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        return response.json().get("access_token", "Error: Access token not found.")
    return f"Error: Failed to generate token. Status: {response.status_code}, Response: {response.text}"