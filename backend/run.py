import asyncio
import sys
import uvicorn
import os

if __name__ == "__main__":
    # Set the correct event loop policy for Windows + Playwright
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        print("✅ AsyncIO policy set for Windows (via run.py).")

    # Run Uvicorn programmatically
    # We use "app.main:app" string so reload works
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
