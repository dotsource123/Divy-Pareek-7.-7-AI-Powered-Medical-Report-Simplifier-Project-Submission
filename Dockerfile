# Stage 1: Builder stage to install Python dependencies
FROM python:3.11-slim AS builder

# Set the working directory in the container
WORKDIR /app

# Create a virtual environment
RUN python -m venv /opt/venv

# Set the PATH to use the venv's pip
ENV PATH="/opt/venv/bin:$PATH"

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies into the virtual environment
RUN pip install --no-cache-dir -r requirements.txt


# Stage 2: Final production image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install Tesseract OCR, which is a system dependency
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && \
    # Clean up the apt cache to reduce image size
    rm -rf /var/lib/apt/lists/*

# Copy the virtual environment with installed packages from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy your application's source code into the container
COPY ./app ./app

# Set the PATH to use the virtual environment's executables
ENV PATH="/opt/venv/bin:$PATH"

# Expose the port that the application will run on
EXPOSE 8000

# The command to run your application
# We use 0.0.0.0 to make it accessible outside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]