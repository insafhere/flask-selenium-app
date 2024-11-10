# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && \
    apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Chromium
ENV CHROMIUM_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/bin/chromedriver

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install Python dependencies from the requirements.txt file
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5000 available to the world outside the container
EXPOSE 5000

# Install gunicorn
RUN pip install gunicorn

# Run with gunicorn for production environments
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
