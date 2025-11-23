# 1. Use a lightweight Python version
FROM python:3.11-slim

# 2. Install FFmpeg (CRITICAL STEP)
# We use apt-get because this is a Linux container, not Windows.
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# 3. Set working directory
WORKDIR /app

# 4. Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application code
COPY . .

# 6. Create the downloads directory and set permissions
RUN mkdir -p downloads && chmod 777 downloads

# 7. Expose the port
EXPOSE 8000

# 8. Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
