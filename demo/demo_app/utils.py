# utils.py — shared utilities

from demo_app.config import DATABASE_URL   # ← uses the OLD name; PR renames it


def get_db_connection():
    """Return a DB connection using the configured URL."""
    import psycopg2
    return psycopg2.connect(DATABASE_URL)


def paginate(items: list, page: int, page_size: int = 20) -> list:
    start = (page - 1) * page_size
    return items[start : start + page_size]
