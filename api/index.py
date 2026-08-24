import sys
import os

# Ensure Python can find main.py in the root folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app