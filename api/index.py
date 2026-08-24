import sys
import os

# Add root folder to sys.path so Vercel can see main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app