# Companies Data Extractor (MCA Extraction Engine v2.0)

A high-performance, professional-grade desktop automation system designed for high-volume data extraction from the MCA portal. This system features a premium React dashboard, robust process management, and advanced security protocols.

![Dashboard Preview](assets/dashboard_preview.png)

## 🚀 Key Features

*   **Premium Dashboard**: Sleek, glassmorphic UI built with React and Tailwind-style vanilla CSS.
*   **Pro Layout**: Independent scrolling columns and fixed-height controls ensure a rock-solid user experience on any screen size.
*   **VPN Kill-Switch**: Real-time security monitoring that automatically aborts extraction if the VPN connection drops, protecting your IP integrity.
*   **Native Windows Integration**: Custom VBScript and PowerShell bridging to bypass Windows foreground locks for Excel and Folder selection.
*   **Smart Reliability**:
    *   **Sleep Prevention**: Keeps the PC awake during long extraction sessions.
    *   **Auto-Shutdown**: The system automatically kills background processes 15 seconds after the browser tab is closed.
    *   **Bulletproof Parsing**: Robust Excel handling that accounts for empty rows, hidden spaces, and case-insensitive headers.

## 🛠 Tech Stack

*   **Frontend**: React.js, Lucide Icons, Vanilla CSS (Modern Aesthetics)
*   **Backend**: Python (FastAPI), Uvicorn
*   **Engine**: Custom Scraper logic with VPN-aware security layers
*   **Automation**: VBScript, PowerShell, COM Objects

## 📂 Project Structure

*   `MCA_Portable_App/`: The standalone, client-ready version of the application.
*   `frontend/`: Source code for the React dashboard.
*   `api.py`: FastAPI backend coordinator.
*   `scraper.py`: Core extraction engine.
*   `config.py`: System configuration and limits.

## 🏁 Quick Start (Portable Mode)

1.  Navigate to the `MCA_Portable_App/` directory.
2.  Double-click `Start_MCA_Engine.bat`.
3.  The dashboard will automatically open in your default browser at `http://localhost:8000`.

## 👨‍💻 Development Setup

### Backend
1. Install Python 3.8+
2. Install dependencies: `pip install -r requirements.txt`
3. Run the server: `python api.py`

### Frontend
1. Navigate to `frontend/`
2. Install dependencies: `npm install`
3. Start dev server: `npm run dev`
4. Build for production: `npm run build`

## 📜 Usage Guidelines

1.  **Input**: Select an Excel file containing a list of CIN numbers.
2.  **Output**: Manually select a save destination via the "Save Path" button.
3.  **Start**: Click "Start Extraction." Monitor progress and system logs in real-time.
4.  **Security**: Ensure your VPN (e.g., ProtonVPN) is active before starting. The system will alert you if the connection is lost.

---
**Developed with ❤️ for Professional Data Extraction Workflows.**
