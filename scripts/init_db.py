"""
FinanceSim — Database initializer
Called by run.bat to ensure tables exist.
"""
import sys
sys.path.insert(0, '.')
import asyncio
from app.database import init_db

asyncio.run(init_db())
print('OK')
