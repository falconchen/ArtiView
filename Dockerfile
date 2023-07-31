# Use the official Python image as a base image
FROM python:3.9-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY ./requirements.txt /app

# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the main.py file into the container
COPY ./app /app

# Expose port 8000
EXPOSE 8000

# Command to run the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000","--reload"]
