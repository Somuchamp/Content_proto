# Use the official lightweight Python 3.11 image
FROM python:3.11-slim

# Set system environment variables to optimize Python performance
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies (curl/git/bash are helpful for debugging & networking)
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements to leverage Docker's caching layer
COPY requirements.txt .

# Install Python package dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire workspace code (honoring .dockerignore exclusions)
COPY . .

# Grant execution permissions to the supervisor startup script
RUN chmod +x start.sh

# Expose default Streamlit port (Railway will map this dynamically at runtime)
EXPOSE 8501

# Run the unified start script to launch FastAPI and Streamlit concurrently
CMD ["/bin/bash", "./start.sh"]
