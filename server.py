from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import logging
import socket
import asyncio
from typing import Dict, Set
import time

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

# Store connected WebSocket clients with metadata
class ClientConnection:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.last_activity = time.time()
        self.buffer_size = 2048  # Dynamic buffer size (can be adjusted based on network conditions)
        self.data_queue = asyncio.Queue()  # Queue for outgoing messages
        
connected_clients: Set[ClientConnection] = set()

# Server statistics
class ServerStats:
    def __init__(self):
        self.total_messages = 0
        self.bytes_transferred = 0
        self.start_time = time.time()
        
    def add_message(self, size_bytes: int):
        self.total_messages += 1
        self.bytes_transferred += size_bytes
        
    def get_throughput(self):
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            return self.bytes_transferred / elapsed
        return 0

server_stats = ServerStats()

@app.get("/", response_class=HTMLResponse)
async def get():
    try:
        with open("static/index.html") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        logger.error("index.html not found in static directory")
        return HTMLResponse(content="Error: index.html not found", status_code=404)

async def client_sender(client: ClientConnection):
    """Background task to send queued audio data to clients"""
    try:
        while True:
            # Get data from queue (with timeout to allow for connection checks)
            try:
                data = await asyncio.wait_for(client.data_queue.get(), timeout=0.5)
                await client.websocket.send_bytes(data)
                client.last_activity = time.time()
            except asyncio.TimeoutError:
                # Check if client is still active
                if time.time() - client.last_activity > 30:  # 30 seconds timeout
                    logger.info("Client connection timed out")
                    break
                await asyncio.sleep(0.01)  # Small sleep to prevent CPU spinning
    except Exception as e:
        logger.error(f"Error in client sender task: {e}")
    finally:
        if client in connected_clients:
            connected_clients.remove(client)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client = ClientConnection(websocket)
    connected_clients.add(client)
    
    # Start background task for sending data to this client
    sender_task = asyncio.create_task(client_sender(client))
    
    logger.info(f"Client connected. Total clients: {len(connected_clients)}")
    try:
        while True:
            # Receive audio data (binary)
            data = await websocket.receive_bytes()
            client.last_activity = time.time()
            
            # Update server statistics
            server_stats.add_message(len(data))
            
            # Log throughput occasionally
            if server_stats.total_messages % 1000 == 0:
                throughput = server_stats.get_throughput() / 1024  # KB/s
                logger.info(f"Current throughput: {throughput:.2f} KB/s")
                
            # Broadcast to all other clients using their queues (non-blocking)
            for other_client in connected_clients:
                if other_client != client:
                    # Add to queue with no wait - drop if queue is full (to prevent backlog)
                    try:
                        other_client.data_queue.put_nowait(data)
                    except asyncio.QueueFull:
                        logger.warning("Queue full for a client, dropping packet")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Cancel sender task and remove client
        sender_task.cancel()
        try:
            await sender_task
        except asyncio.CancelledError:
            pass
        
        if client in connected_clients:
            connected_clients.remove(client)
        await websocket.close()
        logger.info(f"Client disconnected. Total clients: {len(connected_clients)}")

if __name__ == "__main__":
    import uvicorn
    local_ip = get_local_ip()
    logger.info(f"Starting server. Access it at:")
    logger.info(f" - On this computer: http://localhost:8000")
    logger.info(f" - On other devices (e.g., mobile): http://{local_ip}:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)