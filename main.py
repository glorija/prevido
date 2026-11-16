from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic_settings import BaseSettings
import os
import uuid
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "")
    app_password: str = os.getenv("APP_PASSWORD", "prevido2026")  # privremena zaštita
    max_file_size_mb: int = 200

settings = Settings()

app = FastAPI(title="Prevido")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Privremena jednostavna autentikacija (lozinka)
def check_auth(request: Request):
    password = request.cookies.get("prevido_auth")
    if password != settings.app_password:
        return False
    return True

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if not check_auth(request):
        return templates.TemplateResponse("login.html", {"request": request})
    return templates.TemplateResponse("index.html", {
        "request": request,
        "languages": [
            {"code": "hr", "name": "Hrvatski"},
            {"code": "en", "name": "English"},
            {"code": "de", "name": "Deutsch"},
            {"code": "fr", "name": "Français"},
            {"code": "es", "name": "Español"},
            {"code": "it", "name": "Italiano"},
            {"code": "ru", "name": "Русский"},
            {"code": "uk", "name": "Українська"},
        ]
    })

@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    if password == settings.app_password:
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="prevido_auth", value=password, httponly=True, max_age=60*60*24*7)
        return response
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Pogrešna lozinka"
    })

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("prevido_auth")
    return response

@app.post("/upload")
async def upload_video(
    request: Request,
    file: UploadFile = File(...),
    target_lang: str = Form(...)
):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Validacija
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Molimo uploadajte video datoteku")

    # Generiraj jedinstveni ID
    job_id = str(uuid.uuid4())
    file_ext = Path(file.filename).suffix or ".mp4"
    input_path = UPLOAD_DIR / f"{job_id}{file_ext}"
    output_path = OUTPUT_DIR / f"{job_id}_translated.mp4"

    # Spremi datoteku
    content = await file.read()
    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Datoteka je prevelika (max {settings.max_file_size_mb}MB)")

    with open(input_path, "wb") as f:
        f.write(content)

    # TODO: Ovdje ide prava obrada (ElevenLabs + FFmpeg)
    # Za sada samo kopiramo original kao placeholder
    import shutil
    shutil.copy(input_path, output_path)

    return {
        "job_id": job_id,
        "status": "completed",  # kasnije: processing
        "message": "Video je uspješno uploadan. Obrada dolazi uskoro.",
        "download_url": f"/download/{job_id}"
    }

@app.get("/download/{job_id}")
async def download(job_id: str, request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    output_path = OUTPUT_DIR / f"{job_id}_translated.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Video nije pronađen")

    return FileResponse(
        path=output_path,
        filename=f"prevido_{job_id}.mp4",
        media_type="video/mp4"
    )

@app.get("/health")
async def health():
    return {"status": "ok", "app": "Prevido"}
