# 1. Use Alpine Linux (Extremely lightweight & fast)
FROM python:3.11-alpine

# 2. Install FFmpeg and Git
# We use 'apk' instead of 'apt-get'. It is instant and uses very little RAM.
RUN apk add --no-cache ffmpeg git

# 3. Set working directory
WORKDIR /app

# 4. Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the application code
COPY . .

# 6. Create downloads folder and set permissions
RUN mkdir -p downloads && chmod 777 downloads

# 7. Expose the port
EXPOSE 8000

# 8. Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
