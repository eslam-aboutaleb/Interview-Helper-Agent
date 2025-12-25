FROM python:3.11-slim

# Set the working directory within the container
WORKDIR /app

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy requirements file
COPY requirements.txt .

# Install virtualenv, set up virtual environment, and install dependencies
RUN pip install virtualenv && \
    virtualenv /app/venv && \
    . /app/venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the container
COPY . .

# Set ownership to the non-root user
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose port 8000 for the FastAPI application
EXPOSE 8000

# Set environment variable to use the virtual environment
ENV PATH="/app/venv/bin:$PATH"

# Start the FastAPI server using uvicorn within the virtual environment
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]