import os
import uuid
import traceback
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
DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def cleanup_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

# ==========================================
# DOWNLOAD TASK
# ==========================================
def processing_task(url: str, filename_template: str):
    # RELIABLE CONFIGURATION FOR SERVERS
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{filename_template}.%(ext)s',
        'noplaylist': True,
        
        # --- NETWORK FIXES (The Solution) ---
        'force_ipv4': True,  # CRITICAL: Fixes 403 on Docker/Cloud
        'source_address': '0.0.0.0',
        
        # --- SPEED ---
        'concurrent_fragment_downloads': 3, # Lowered slightly for stability
        'buffersize': 1024 * 1024,
        'retries': 5,
        
        # --- STEALTH MODE ---
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },
        
        # --- AUDIO CONVERSION ---
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        
        # --- ERROR HANDLING ---
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info.get('title', 'audio')

@app.get("/")
def home():
    return {"status": "running", "platform": "linux-docker-v2"}

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
        
        safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        
    except Exception as e:
        # LOG THE REAL ERROR
        error_trace = traceback.format_exc()
        print(f"❌ CRITICAL ERROR:\n{error_trace}")
        
        # Return the specific error to the user/frontend so we know what to fix
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

    mp3_file_path = f"{filename_template}.mp3"

    if not os.path.exists(mp3_file_path):
        raise HTTPException(status_code=500, detail="Conversion failed - FFmpeg might be missing or file was not written.")

    background_tasks.add_task(cleanup_file, mp3_file_path)

    return FileResponse(
        path=mp3_file_path,
        filename=f"{safe_title}.mp3",
        media_type="audio/mpeg"
    )
