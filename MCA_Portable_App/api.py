import os
import threading
import sys
import io
import datetime
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import pandas as pd

import scraper
import time
import ctypes
import config
import subprocess

def check_vpn_active():
    try:
        cmd_vpn = ["powershell", "-Command", "Get-VpnConnection -ErrorAction SilentlyContinue | Where-Object { $_.ConnectionStatus -eq 'Connected' }"]
        res = subprocess.run(cmd_vpn, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if res.stdout.strip(): 
            return True
        
        keywords = "'Proton|WireGuard|TUN|TAP'"
        cmd_adapter = ["powershell", "-Command", f"Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object {{ $_.Status -eq 'Up' -and ($_.InterfaceDescription -match {keywords} -or $_.Name -match {keywords}) }} | Select-Object -ExpandProperty Name"]
        res2 = subprocess.run(cmd_adapter, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        
        detected = res2.stdout.strip()
        if detected:
            # For debugging, we'll print it to the console
            # print(f"[Debug] VPN Detected via Adapter: {detected}")
            return True
        return False
    except Exception as e:
        print(f"[KillSwitch] Error checking VPN status: {e}")
        return False

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Windows Sleep Prevention Constants
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_AWAYMODE_REQUIRED = 0x00000040

def prevent_sleep():
    if os.name == 'nt': # Windows only
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED)
        print("[System] Sleep prevention ENABLED.")

def allow_sleep():
    if os.name == 'nt': # Windows only
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        print("[System] Sleep prevention DISABLED.")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state to keep track of the scraping process
scraper_state = {
    "is_running": False,
    "logs": [],
    "progress": 0,
    "total": 0,
    "pending": 0,
    "input_file": None,
    "output_file": None,
    "error": None
}

stop_event = threading.Event()
last_heartbeat = time.time()
first_heartbeat_received = False
disconnect_received = False

def monitor_heartbeat():
    global first_heartbeat_received, last_heartbeat
    last_check_time = time.time()
    
    while True:
        time.sleep(5)
        current_time = time.time()
        
        # Detect System Sleep/Suspend
        # If the gap between checks is > 15s (expected is 5s), the PC likely slept
        if current_time - last_check_time > 15:
            print(f"\n[System] System wake detected (Gap: {int(current_time - last_check_time)}s). Resetting heartbeat...")
            last_heartbeat = current_time # Reset heartbeat to prevent immediate shutdown
            
        last_check_time = current_time

        # LIVE VPN KILL SWITCH - Instant background check every 5 seconds
        if scraper_state["is_running"]:
            if not check_vpn_active():
                msg = "[!!!] CRITICAL SECURITY ALERT: VPN DISCONNECTED! [!!!]"
                print(f"\n\n{msg}")
                scraper_state["logs"].append(msg)
                scraper_state["logs"].append("[!!!] The extraction has been automatically aborted to protect your real IP address.")
                stop_event.set()

        if first_heartbeat_received:
            if disconnect_received:
                # Tab was explicitly closed or refreshed. Wait 15s to see if it comes back.
                if current_time - last_heartbeat > 15: 
                    print("\n[!] Browser connection closed for > 15s. Shutting down system...")
                    stop_event.set()
                    time.sleep(2)
                    os._exit(0)
        else:
            # Wait 5 minutes for the first connection
            if current_time - last_heartbeat > 300:
                print("\n[!] No browser connection detected after 5m. Shutting down...")
                os._exit(0)

# Start monitor thread
threading.Thread(target=monitor_heartbeat, daemon=True).start()

class ListStream(io.StringIO):
    def write(self, string):
        if not string:
            return
            
        # If the string contains a carriage return \r, we try to overwrite the last log entry
        if '\r' in string:
            # Split by \r to get the latest content
            parts = string.split('\r')
            latest = parts[-1].strip()
            if latest:
                if scraper_state["logs"]:
                    scraper_state["logs"][-1] = latest
                else:
                    scraper_state["logs"].append(latest)
        elif string.strip():
            # Standard print with a newline or just text
            scraper_state["logs"].append(string.strip())
            
        super().write(string)

def run_scraper_background(input_path: str, output_path: str, delay_min: int, delay_max: int, total: int, pending: int):
    scraper_state["is_running"] = True
    scraper_state["logs"] = []
    scraper_state["error"] = None
    scraper_state["input_file"] = input_path
    scraper_state["output_file"] = output_path
    scraper_state["total"] = total
    scraper_state["pending"] = pending
    stop_event.clear()
    
    # Prevent system from sleeping while engine is active
    prevent_sleep()
    
    # Redirect stdout to capture prints
    old_stdout = sys.stdout
    sys.stdout = ListStream()
    
    try:
        scraper.run(
            input_file=input_path,
            output_file=output_path,
            delay_range=(delay_min, delay_max),
            stop_event=stop_event,
            progress_callback=lambda p, t: scraper_state.update({"progress": p, "total": t})
        )
    except Exception as e:
        scraper_state["error"] = str(e)
        print(f"[!] Critical Error: {str(e)}")
    finally:
        scraper_state["is_running"] = False
        sys.stdout = old_stdout
        # Allow system to sleep again
        allow_sleep()

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    os.makedirs("input", exist_ok=True)
    file_path = f"input/{file.filename}"
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Check record count
    try:
        df = pd.read_excel(file_path, header=None)
        # Find header row
        header_row = None
        for i, row in df.iterrows():
            if any("CIN" in str(cell).upper() for cell in row):
                header_row = i
                break
        
        if header_row is None:
            return JSONResponse(status_code=400, content={"message": "Could not find 'CIN' column in the uploaded file."})
        
        data_rows = df.index[header_row + 1:]
        total_records = len(data_rows)
        
        if total_records > config.MAX_RECORDS_PER_FILE:
            return JSONResponse(status_code=400, content={
                "message": f"File contains {total_records} records. Please add a file with less than {config.MAX_RECORDS_PER_FILE} records.",
                "total": total_records
            })

        # Calculate pending records
        df.columns = df.iloc[header_row]
        pending_count = total_records
        if 'Status' in df.columns:
            statuses = df['Status'].iloc[header_row+1:].astype(str).str.strip().tolist()
            exported_count = sum(1 for s in statuses if s == "Exported")
            pending_count = total_records - exported_count

        return {
            "filename": file.filename, 
            "path": file_path, 
            "total": total_records,
            "pending": pending_count
        }
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": f"Error processing file: {str(e)}"})

@app.get("/select-input-path")
def select_input_path():
    print("[UI] Request: Opening Input File Dialog (Isolated)...")
    import subprocess
    
    # Run a tiny isolated python script to handle the GUI window
    gui_script = (
        "import tkinter as tk; from tkinter import filedialog; "
        "root=tk.Tk(); root.withdraw(); root.attributes('-topmost',True); "
        "path=filedialog.askopenfilename(title='Select Input CIN Excel File', "
        "filetypes=[('Excel files', '*.xlsx *.xls'), ('All files', '*.*')]); "
        "print(path); root.destroy()"
    )
    
    try:
        result = subprocess.run([sys.executable, "-c", gui_script], capture_output=True, text=True, check=True)
        file_path = result.stdout.strip()
        
        if file_path:
            print(f"[UI] Selected: {file_path}")
            # Get record count and metadata
            try:
                df = pd.read_excel(file_path, header=None)
                header_row = None
                for i, row in df.iterrows():
                    if any("CIN" in str(cell).upper() for cell in row):
                        header_row = i
                        break
                
                if header_row is None:
                    return JSONResponse(status_code=400, content={"message": "Could not find 'CIN' column in the selected file."})
                
                data_rows = df.index[header_row + 1:]
                total_records = len(data_rows)
                
                if total_records > config.MAX_RECORDS_PER_FILE:
                    return JSONResponse(status_code=400, content={
                        "message": f"File contains {total_records} records. Please add a file with less than {config.MAX_RECORDS_PER_FILE} records.",
                        "total": total_records
                    })

                # Calculate pending records
                # Ensure we handle duplicate columns by using unique names if needed
                df_temp = df.copy()
                df_temp.columns = [str(c).strip() for c in df.iloc[header_row]]
                print(f"[DEBUG] Found Columns: {list(df_temp.columns)}")
                
                pending_count = total_records
                # Look for 'Status' column specifically
                status_col = None
                for col in df_temp.columns:
                    if str(col).strip().lower() == 'status':
                        status_col = col
                        break
                
                if status_col is not None:
                    # Get only the data rows after the header
                    # Use .iloc to skip header row and conversion to string to be safe
                    all_rows = df_temp[status_col].tolist()
                    data_statuses = all_rows[header_row + 1:]
                    
                    exported_count = 0
                    for s in data_statuses:
                        if str(s).strip().lower() == "exported":
                            exported_count += 1
                            
                    pending_count = total_records - exported_count
                    print(f"[DEBUG] Records: Total={total_records}, Exported={exported_count}, Pending={pending_count}")

                scraper_state["input_file"] = file_path
                scraper_state["total"] = total_records
                scraper_state["pending"] = pending_count
                scraper_state["progress"] = 0
                scraper_state["logs"] = []
                scraper_state["error"] = None

                return {
                    "path": file_path, 
                    "total": total_records,
                    "pending": pending_count
                }
            except Exception as e:
                print(f"Excel read error: {e}")
                return JSONResponse(status_code=400, content={"message": "INVALID EXCEL FILE: This file is either corrupted or not a valid Excel workbook. Please check the file and try again."})
        return {"path": None}
    except Exception as e:
        print(f"Isolated picker error: {e}")
        return JSONResponse(status_code=500, content={"message": "Failed to open file dialog."})

@app.get("/select-output-path")
def select_output_path(input_filename: str):
    print(f"[UI] Request: Opening Output File Dialog for {input_filename} (Isolated)...")
    import subprocess
    
    base_name = os.path.splitext(input_filename)[0]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    default_filename = f"{base_name}_Output_{timestamp}.xlsx"
    
    # Run a tiny isolated python script to handle the GUI window
    gui_script = (
        "import tkinter as tk; from tkinter import filedialog; "
        "root=tk.Tk(); root.withdraw(); root.attributes('-topmost',True); "
        "path=filedialog.asksaveasfilename(title='Select Output Save Location', "
        "defaultextension='.xlsx', initialfile='" + default_filename + "', "
        "filetypes=[('Excel files', '*.xlsx'), ('All files', '*.*')]); "
        "print(path); root.destroy()"
    )
    
    try:
        result = subprocess.run([sys.executable, "-c", gui_script], capture_output=True, text=True, check=True)
        file_path = result.stdout.strip()
        
        if file_path:
            print(f"[UI] Selected Output: {file_path}")
            return {"path": file_path}
        return {"path": None}
    except Exception as e:
        print(f"Isolated picker error: {e}")
        return JSONResponse(status_code=500, content={"message": "Failed to open save dialog."})

@app.post("/start")
async def start_scraping(background_tasks: BackgroundTasks, input_file: str, output_path: str = Query(...), total: int = 0, pending: int = 0):
    if scraper_state["is_running"]:
        return JSONResponse(status_code=400, content={"message": "Scraper is already running"})
    
    background_tasks.add_task(run_scraper_background, input_file, output_path, config.DELAY_MIN_SECONDS, config.DELAY_MAX_SECONDS, total, pending)
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

@app.post("/heartbeat")
async def heartbeat():
    global last_heartbeat, first_heartbeat_received, disconnect_received
    last_heartbeat = time.time()
    first_heartbeat_received = True
    disconnect_received = False
    return {"status": "ok"}

@app.post("/disconnect")
async def disconnect():
    global disconnect_received
    disconnect_received = True
    return {"status": "disconnecting"}

@app.get("/download")
async def download_results():
    if not scraper_state["output_file"] or not os.path.exists(scraper_state["output_file"]):
        return JSONResponse(status_code=404, content={"message": "Output file not found"})
    return FileResponse(
        scraper_state["output_file"], 
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        filename="MCA_Data_Extracter_Results.xlsx"
    )

@app.get("/open-file")
async def open_file(path: str = Query(...)):
    try:
        norm_path = os.path.abspath(os.path.normpath(path))
        print(f"[UI] Opening File: {norm_path}")
        if not os.path.exists(norm_path):
            return JSONResponse(status_code=404, content={"message": "File not found. It will be created once the first record is extracted."})
        
        # Use ShellExecute via PowerShell, which is the most reliable way to force focus
        import subprocess
        cmd = f'powershell -Command "(New-Object -ComObject Shell.Application).ShellExecute(\'{norm_path}\')"'
        subprocess.Popen(cmd, shell=True)
        return {"status": "success"}
    except Exception as e:
        print(f"[ERROR] Could not open file: {e}")
        return JSONResponse(status_code=500, content={"message": str(e)})

@app.get("/open-folder")
async def open_folder(path: str = Query(...)):
    try:
        norm_path = os.path.abspath(os.path.normpath(path))
        print(f"[UI] Opening Folder (VBS Trick): {norm_path}")
        
        if not os.path.exists(norm_path):
            return JSONResponse(status_code=404, content={"message": "File not found."})

        # The VBScript 'AppActivate' trick is the most powerful way to bypass foreground locks.
        import tempfile
        vbs_content = f'''
Set objShell = CreateObject("Wscript.Shell")
objShell.Run "explorer.exe /select,""{norm_path}"""
WScript.Sleep 1000
objShell.AppActivate "File Explorer"
'''
        with tempfile.NamedTemporaryFile(delete=False, suffix=".vbs") as f:
            f.write(vbs_content.encode('utf-8'))
            vbs_path = f.name
            
        import subprocess
        subprocess.Popen(['wscript.exe', vbs_path])
        
        # We don't delete immediately to give wscript time to read it
        return {"status": "success"}
    except Exception as e:
        print(f"[ERROR] Could not open folder: {e}")
        return JSONResponse(status_code=500, content={"message": str(e)})

# Mount the React frontend (at the end so it doesn't override API routes)
frontend_path = get_resource_path("frontend/dist")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
