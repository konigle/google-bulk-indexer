import json
import os

from google.auth.transport.requests import Request
from google.oauth2 import service_account

SCOPES = [
    "https://www.googleapis.com/auth/indexing",
    "https://www.googleapis.com/auth/webmasters.readonly",
]


def get_access_token(credentials_path: str = "./service_account.json") -> str:
    """Get access token from service account credentials.

    Args:
        credentials_path (str, optional): Path to the service account
            credentials file.
            Defaults to "./service_account.json".

    Raises:
        FileNotFoundError: If the credentials file is not found.

    Returns:
        str: Access token.
    """
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            f"Credentials file not found at {credentials_path}"
        )
    with open(credentials_path) as f:
        credentials_info = json.load(f)
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info
    )
    scoped_credentials = credentials.with_scopes(SCOPES)
    scoped_credentials.refresh(Request())
    return scoped_credentials.token
