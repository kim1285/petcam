"""
monitor house using webcam
stream video of house to website using fastapi.
many people should be able to access the video real time. 1 directional.
fastapi server provides video to browser.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
import cv2
import asyncio
import threading
from collections import deque
import time

# shared buffer object (fixed size)
frame_buffer = deque(maxlen=1)


# frame generator
def set_frames(stop_event: threading.Event):
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Cannot open camera")
            return
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                continue
            ret, jpeg = cv2.imencode(".jpg", frame.copy())
            if not ret:
                continue
            frame_buffer.append(jpeg.tobytes())
            time.sleep(0.034)  # 1/30 ~= 0.0333.. sec for 30 fps camera.
    except Exception as e:
        print(f"Error while setting frames: {e}")


# frame consumer
async def get_frames():
    await asyncio.sleep(0.1)
    while True:
        try:
            # return control to main fastapi async loop to get request momentarily
            await asyncio.sleep(0)
            # get the frame
            if not frame_buffer:
                continue
            jpeg_bytes = frame_buffer[-1]
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n'
        except Exception as e:
            raise Exception(f"error while getting frames: {e}.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # setup code (runs at app startup)
    # start frame generator thread
    stop_event = threading.Event()
    try:
        camera_thread = threading.Thread(target=set_frames, args=(stop_event,), daemon=True)
        camera_thread.start()
        yield  # app runs
    except Exception as e:
        raise Exception(f"{e}")
    finally:
        # cleanup code (runs at app shutdown)
        stop_event.set()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def home():
    return {"status": "ok"}


@app.get("/video")
async def video_feed():
    return StreamingResponse(get_frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/video_page")
async def video_page():
    html_content = """  
    <html>        <head>            <title>Webcam Stream</title>        </head>        <body>            <h1>Live Webcam</h1>            <img src="/video" width="640" height="480"/>        </body>    </html>    """
    return HTMLResponse(content=html_content)