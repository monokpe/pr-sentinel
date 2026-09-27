# config.py — app configuration
# NOTE: in the PR, DATABASE_URL was renamed to DB_CONNECTION_STRING
# but api.py (the changed file) still references the old name

DATABASE_URL = "postgresql://localhost/myapp"   # old name — about to be renamed
# DB_CONNECTION_STRING = "postgresql://localhost/myapp"  # new name (in PR)

SECRET_KEY = "change-me-in-production"
DEBUG = False
MAX_PAGE_SIZE = 100
