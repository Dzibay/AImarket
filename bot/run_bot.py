"""
Локальный запуск бота на Windows:

  cd bot
  python run_bot.py
"""

from __future__ import annotations

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    from app.main import main

    asyncio.run(main())
