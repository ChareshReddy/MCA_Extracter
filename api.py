import os
import threading
import sys
import io
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

import instafinancials_scraper

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
os.makedirs("input", exist_ok=True)
os.makedirs("output", exist_ok=True)


# Global state to keep track of the scraping process
scraper_state = {
    "is_running": False,
    "logs": [],
    "progress": 0,
    "total": 0,
    "output_file": None,
    "error": None
}

stop_event = threading.Event()

class ListStream(io.StringIO):
    def write(self, string):
        if string.strip():
            scraper_state["logs"].append(string.strip())
        super().write(string)

def run_scraper_background(input_path: str, output_path: str, delay_min: int, delay_max: int):
    scraper_state["is_running"] = True
    scraper_state["logs"] = []
    scraper_state["error"] = None
    scraper_state["output_file"] = output_path
    stop_event.clear()
    
    # Redirect stdout to capture prints
    old_stdout = sys.stdout
    sys.stdout = ListStream()
    
    try:
        instafinancials_scraper.run(
            input_file=input_path,
            output_file=output_path,
            delay_range=(delay_min, delay_max),
            stop_event=stop_event
        )
    except Exception as e:
        scraper_state["error"] = str(e)
        print(f"[!] Critical Error: {str(e)}")
    finally:
        scraper_state["is_running"] = False
        sys.stdout = old_stdout

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    os.makedirs("input", exist_ok=True)
    file_path = f"input/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return {"filename": file.filename, "path": file_path}

@app.post("/start")
async def start_scraping(background_tasks: BackgroundTasks, input_file: str):
    if scraper_state["is_running"]:
        return JSONResponse(status_code=400, content={"message": "Scraper is already running"})
    
    output_file = "output/Pankaj_Vikram_Extracted_data.xlsx"
    # Hardcoded delays as requested: 30 to 300
    background_tasks.add_task(run_scraper_background, input_file, output_file, 30, 300)
    return {"message": "Scraping started"}

@app.post("/stop")
async def stop_scraping():
    if not scraper_state["is_running"]:
        return JSONResponse(status_code=400, content={"message": "Scraper is not running"})
    stop_event.set()
    return {"message": "Stop signal sent"}

@app.get("/status")
async def get_status():
    return scraper_state

@app.get("/download")
async def download_results():
    if not scraper_state["output_file"] or not os.path.exists(scraper_state["output_file"]):
        return JSONResponse(status_code=404, content={"message": "Output file not found"})
    return FileResponse(
        scraper_state["output_file"], 
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        filename="Pankaj_Vikram_Extracted_data.xlsx"
    )

# Mount the React frontend (at the end so it doesn't override API routes)
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
