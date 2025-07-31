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
# We install to this specific directory so we can copy it later
RUN pip install --no-cache-dir -r requirements.txt --target=/install


# --- STAGE 2: The Final Image ---
# Now, we start fresh with a slim Python image.
FROM python:3.11-slim

# Set the working directory in the final container
WORKDIR /app

# **FIX**: Copy both the libraries AND the executables (like gunicorn) from the builder stage
COPY --from=builder /install /usr/local/lib/python3.11/site-packages/
COPY --from=builder /install/bin /usr/local/bin/

# **FIX**: Install the missing pypdf dependency
RUN pip install pypdf

# Copy the application code
COPY . .

# Command to run the application using a production-grade server
# We increase the timeout to 120 seconds to allow for processing
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8000", "--timeout", "120"]