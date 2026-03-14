import threading, time, asyncio
import httpx
from config.config import get_settings

settings = get_settings()
INTERVAL = 300  # seconds; < idle-timeout window_


class KeepAlive:
    _thread = None
    _stop = threading.Event()

    @classmethod
    def _loop(cls):
        while not cls._stop.wait(INTERVAL):
            try:
                # Run async httpx call in the thread
                asyncio.run(cls._async_ping())
            except Exception:
                pass  # swallow network hiccups
    
    @classmethod
    async def _async_ping(cls):
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.get(settings.PING_URL)

    @classmethod
    def start(cls):
        if cls._thread and cls._thread.is_alive():
            return  # already running
        cls._stop.clear()
        cls._thread = threading.Thread(target=cls._loop, daemon=True)
        cls._thread.start()

    @classmethod
    def stop(cls):
        cls._stop.set()
