import asyncio
import sys
import uvicorn
import os

if __name__ == "__main__":
    # Set the correct event loop policy for Windows + Playwright
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        print("✅ AsyncIO policy set for Windows (via run.py).")

    # Run Uvicorn manually to ensure we control the Event Loop
    config = uvicorn.Config(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    # asyncio.run() will create a new event loop using the policy we set above
    asyncio.run(server.serve())
