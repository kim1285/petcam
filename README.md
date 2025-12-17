# Petcam – FastAPI Webcam Streaming

A minimal FastAPI app that streams a local webcam to browsers in real time using MJPEG.  
One-way video streaming; multiple clients can watch concurrently.

## How it works
- OpenCV captures frames from the webcam in a background thread
- Latest frame is stored in a shared in-memory buffer
- FastAPI streams frames to clients via `multipart/x-mixed-replace` (MJPEG)

## Endpoints
- `/` – health check
- `/video` – raw MJPEG video stream
- `/video_page` – simple HTML page to view the stream

## Requirements
- Python 3.10+
- FastAPI
- Uvicorn
- OpenCV (`opencv-python`)

## Run
```bash
pip install fastapi uvicorn opencv-python
uvicorn main:app --host 0.0.0.0 --port 8000
Open: http://localhost:8000/video_page
```

Notes
- Uses a single shared frame buffer (latest frame only)
- Designed for simplicity, not authentication or recording
- Suitable for LAN or prototype use
