FROM python:3.11-slim

# Set the working directory within the container
WORKDIR /app

# Copy requirements file
COPY requirements.txt .
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the container
COPY . .

# Expose port 8000 for the FastAPI application
EXPOSE 8000

# Start the FastAPI server using uvicorn
# --host 0.0.0.0 allows connections from any IP
# --port 8000 specifies the port to listen on
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]