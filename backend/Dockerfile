FROM python:3.11-slim

# Set the working directory within the container
WORKDIR /app

# Install virtualenv
RUN pip install virtualenv

# Create a non-root user
RUN useradd -m appuser

# Create virtual environment and set ownership
RUN python -m virtualenv /app/venv && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Copy requirements file and install dependencies in the virtual environment
COPY --chown=appuser:appuser requirements.txt .
RUN /app/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    /app/venv/bin/pip install uvicorn python-multipart

# Copy the rest of the application code to the container
COPY --chown=appuser:appuser . .

# Expose port 8000 for the FastAPI application
EXPOSE 8000

# Start the FastAPI server using the virtual environment
CMD ["/app/venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]