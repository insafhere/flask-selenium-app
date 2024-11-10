# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install Chromium (without Chromedriver as autoinstaller will handle it)
RUN apt-get update && \
    apt-get install -y chromium && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables for Chromium
ENV CHROMIUM_BIN=/usr/bin/chromium
ENV PYTHONUNBUFFERED=1  

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5000
EXPOSE 5000

# Run the app with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "--timeout", "120", "app:app"]

