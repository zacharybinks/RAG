    #!/bin/sh

    # This script is the new entry point for the container.
    # It ensures that database migrations are applied before the application starts.

    echo "--- [Azure Startup] Running database migrations ---"
    alembic upgrade head

    echo "--- [Azure Startup] Starting Gunicorn server ---"
    # **FIX**: Use the PORT variable provided by Azure App Service.
    # The default is 8000, so this works both locally and in production.
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:${PORT:-8000} --timeout 300
    