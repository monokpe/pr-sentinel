# api.py — THIS IS THE FILE CHANGED IN THE DEMO PR
#
# Intentional bugs introduced for the demo:
#   1. Hardcoded API key (line 9)  → SecurityAgent
#   2. References DATABASE_URL but PR renames it to DB_CONNECTION_STRING → ConsistencyAgent
#   3. Calls get_user(id) but the function now requires (id, include_deleted=False) → ConsistencyAgent
#   4. New /admin endpoint has NO auth check (every other endpoint has one) → ConsistencyAgent + SecurityAgent

from demo_app.config import DATABASE_URL   # ← old name; PR was supposed to use DB_CONNECTION_STRING
from demo_app.auth import require_auth

STRIPE_API_KEY = "DEMO_HARDCODED_KEY_replace_with_env_var"  # ← hardcoded secret! (demo fixture)


def get_user(user_id: int, include_deleted: bool = False) -> dict:
    """Fetch a user by ID.  include_deleted added in a previous PR."""
    conn = DATABASE_URL  # placeholder
    return {"id": user_id, "deleted": include_deleted}


def list_users(token: str, page: int = 1) -> list:
    require_auth(token)
    return paginate_results([], page)


def paginate_results(items: list, page: int) -> list:
    from demo_app.utils import paginate
    return paginate(items, page)


# New endpoint added in this PR — missing auth check!
def admin_delete_user(user_id: int) -> dict:
    """Delete a user. Added in this PR."""
    # BUG: no require_auth() call here unlike every other write endpoint
    user = get_user(user_id)   # ← old signature, doesn't pass include_deleted
    return {"deleted": user_id}
