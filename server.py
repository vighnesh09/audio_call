from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import logging
import socket

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to get local IP address
def get_local_ip():
    try:
        # Create a socket to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to a known external server
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        logger.error(f"Could not get local IP: {e}")
        return "Unknown"

app = FastAPI()

# Mount static directory to serve HTML
app.mount("/static", StaticFiles(directory="static"), name="static")

# Store connected WebSocket clients
connected_clients = set()

@app.get("/", response_class=HTMLResponse)
async def get():
    try:
        with open("static/index.html") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        logger.error("index.html not found in static directory")
        return HTMLResponse(content="Error: index.html not found", status_code=404)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info(f"Client connected. Total clients: {len(connected_clients)}")
    try:
        while True:
            # Receive audio data (binary)
            data = await websocket.receive_bytes()
            # Broadcast to all other clients
            for client in connected_clients:
                if client != websocket:
                    await client.send_bytes(data)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connected_clients.remove(websocket)
        await websocket.close()
        logger.info(f"Client disconnected. Total clients: {len(connected_clients)}")

if __name__ == "__main__":
    import uvicorn
    local_ip = get_local_ip()
    logger.info(f"Starting server. Access it at:")
    logger.info(f" - On this computer: http://localhost:8000")
    logger.info(f" - On other devices (e.g., mobile): http://{local_ip}:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)