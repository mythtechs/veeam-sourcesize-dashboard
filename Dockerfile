FROM python:3.12-slim

WORKDIR /app

# Copy app code
COPY app.py .

# Install dependencies
RUN pip install --no-cache-dir flask requests

# Expose port
EXPOSE 5000

# Run the app
CMD ["python", "app.py"]