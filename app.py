from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import yt_dlp
import io
import urllib.parse

app = FastAPI(title="Kareo Studio Engine")

# Frontend se direct connection allow karein
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "running", "engine": "Kareo Studio Native YT Engine"}

@app.get("/api/info")
def get_info(url: str = Query(...)):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'extract_flat': False,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'tv_embedded', 'web']
            }
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", "Video"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "channel": info.get("uploader", "YouTube Creator"),
                "id": info.get("id")
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/download")
def download_stream(url: str = Query(...), format: str = Query("mp4"), resolution: str = Query("720p")):
    """
    Directly extracts and streams the video/audio link straight to the user
    using Android/iOS client emulation to bypass cloud IP blocks.
    """
    clean_res = resolution.replace("p", "")
    
    if format in ["mp3", "wav"]:
        format_selector = "bestaudio/best"
    else:
        # Match resolution (1080p, 720p, 480p, 360p) with audio merged
        format_selector = f"best[height<={clean_res}][ext=mp4]/best[height<={clean_res}]/best"

    ydl_opts = {
        'format': format_selector,
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'tv_embedded']
            }
        },
        'http_headers': {
            'User-Agent': 'com.google.android.youtube/19.09.37 (Linux; U; Android 14) gzip'
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            direct_media_url = info.get("url")

            # Fallback agar requested format direct stream URL na de
            if not direct_media_url and 'formats' in info:
                for fmt in reversed(info['formats']):
                    if fmt.get('url') and fmt.get('acodec') != 'none':
                        direct_media_url = fmt.get('url')
                        break

            if direct_media_url:
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url=direct_media_url)
            else:
                raise HTTPException(status_code=500, detail="Stream URL not extracted")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
