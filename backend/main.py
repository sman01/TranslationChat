from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import List, Dict

app = FastAPI()

# In-memory storage for simplicity
rooms = {}
guest_requests = {}
approved_guests = {}
connections: Dict[str, List[WebSocket]] = {}


class RoomCreateRequest(BaseModel):
    host_username: str
    host_language: str
    guest_language: str


class GuestRequest(BaseModel):
    nickname: str


@app.post("/room/create/")
async def create_room(request: RoomCreateRequest):
    room_id = f"{request.host_username}-{request.host_language}-{request.guest_language}"
    rooms[room_id] = {
        "host_username": request.host_username,
        "host_language": request.host_language,
        "guest_language": request.guest_language,
        "guests": []
    }
    guest_requests[room_id] = []
    approved_guests[room_id] = []
    connections[room_id] = []
    return {"room_id": room_id, "message": "Room created successfully"}


@app.post("/room/request/{room_id}")
async def request_to_join(room_id: str, request: GuestRequest):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    guest_requests[room_id].append(request.nickname)
    return {"message": "Request to join room sent successfully"}


@app.get("/room/requests/{room_id}")
async def get_guest_requests(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return {"guest_requests": guest_requests[room_id]}


@app.post("/room/approve/{room_id}/{guest_nickname}")
async def approve_guest(room_id: str, guest_nickname: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    if guest_nickname not in guest_requests[room_id]:
        raise HTTPException(status_code=404, detail="Guest request not found")
    guest_requests[room_id].remove(guest_nickname)
    approved_guests[room_id].append(guest_nickname)
    return {"message": f"Guest {guest_nickname} approved"}


@app.websocket("/ws/{room_id}/{username}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, username: str):
    await websocket.accept()
    connections[room_id].append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            for connection in connections[room_id]:
                if connection != websocket:
                    await connection.send_text(f"{username}: {data}")
    except WebSocketDisconnect:
        connections[room_id].remove(websocket)
        for connection in connections[room_id]:
            await connection.send_text(f"{username} left the chat")


@app.get("/room/start/{room_id}/{guest_nickname}")
async def start_chat(room_id: str, guest_nickname: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    if guest_nickname not in approved_guests[room_id]:
        raise HTTPException(status_code=404, detail="Guest not approved")

    return {"message": f"Chat started with {guest_nickname}",
            "websocket_url": f"ws://localhost:8000/ws/{room_id}/{{username}}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
