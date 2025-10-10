import asyncio
import platform

# ✅ Fix Playwright "NotImplementedError" on Windows
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
