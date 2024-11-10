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

# Expose port 5000 to Render's server
EXPOSE 5000

# Command to run the app using Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
