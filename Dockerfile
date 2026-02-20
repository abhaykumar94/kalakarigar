# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (ffmpeg is required for audio features)
RUN apt-get update && apt-get install -y \
    ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code
COPY . .

# Expose the port that Cloud Run expects (always $PORT, default 8080)
EXPOSE 8080

# Healthcheck (Cloud Run expects on $PORT, so don't hardcode 8501)
HEALTHCHECK CMD curl --fail http://localhost:$PORT/_stcore/health || exit 1

# Run Streamlit (bind to $PORT and 0.0.0.0 for external access)
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true"]
