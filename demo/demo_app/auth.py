# auth.py — authentication helpers

def verify_token(token: str) -> dict | None:
    """
    Verify a JWT token.
    Returns the decoded payload or None if invalid.
    """
    import jwt  # PyJWT
    try:
        return jwt.decode(token, "secret", algorithms=["HS256"])
    except Exception:
        return None


def require_auth(token: str) -> dict:
    """Raise ValueError if token is invalid."""
    payload = verify_token(token)
    if payload is None:
        raise ValueError("Unauthorised")
    return payload
