# Use a full-featured Python base image to avoid compilation issues
FROM python:3.11

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Copy the new startup script and make it executable
COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh

# Use the script as the command to start the container
CMD ["/app/run.sh"]
