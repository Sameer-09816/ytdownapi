import os
import uuid
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
import yt_dlp

app = FastAPI(title="Coolify Music Downloader")

# ==========================================
# CORS
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# CONFIG
# ==========================================
# In Docker, we work relative to the /app folder
DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def cleanup_file(path: str):
    """Deletes file after sending."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

# ==========================================
# DOWNLOAD TASK
# ==========================================
def processing_task(url: str, filename_template: str):
    # Linux/Docker has ffmpeg in the global PATH, so we don't need 'ffmpeg_location'
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{filename_template}.%(ext)s',
        'noplaylist': True,
        
        # Speed & Network Settings
        'concurrent_fragment_downloads': 5, 
        'buffersize': 1024 * 1024,
        'retries': 10,
        'source_address': '0.0.0.0',
        
        # Anti-Bot Headers
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
        
        # Audio Conversion
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info.get('title', 'audio')

@app.get("/")
def home():
    return {"status": "running", "platform": "linux-docker"}

@app.get("/download")
async def download_music(url: str, background_tasks: BackgroundTasks):
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    file_id = str(uuid.uuid4())
    filename_template = f"{DOWNLOAD_DIR}/{file_id}"

    try:
        print(f"🚀 Processing: {url}")
        # Run blocking download in a separate thread
        title = await run_in_threadpool(processing_task, url, filename_template)
        
        # Sanitize title
        safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail="Download failed on server.")

    mp3_file_path = f"{filename_template}.mp3"

    if not os.path.exists(mp3_file_path):
        raise HTTPException(status_code=500, detail="Conversion failed.")

    background_tasks.add_task(cleanup_file, mp3_file_path)

    return FileResponse(
        path=mp3_file_path,
        filename=f"{safe_title}.mp3",
        media_type="audio/mpeg"
    )
