# --- STAGE 1: The Builder ---
# We start with a full-featured Python image that has all the build tools we need.
FROM python:3.11 as builder

# Install system dependencies required for compiling Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /install

# Copy only the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# --- STAGE 2: The Final Image ---
# Now, we start fresh with a slim Python image.
FROM python:3.11-slim

# Set the working directory in the final container
WORKDIR /app

# Copy the installed dependencies from the "builder" stage
COPY --from=builder /install /usr/local/lib/python3.11/site-packages/
# Copy the executables (like gunicorn and alembic) from the builder stage
COPY --from=builder /install/bin /usr/local/bin/

# Copy the application code
COPY . .

# **FIX**: Run the startup commands directly to avoid line-ending issues with run.sh
# This command first runs the database migration and then starts the web server.
CMD ["sh", "-c", "alembic upgrade head && gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000 --timeout 300"]
