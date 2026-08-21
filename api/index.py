import sys
import os

# Points Python to the root directory where main.py sits
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app