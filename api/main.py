# Re-export the main app from api.app so uvicorn api.main:app still works.
from api.app import app
