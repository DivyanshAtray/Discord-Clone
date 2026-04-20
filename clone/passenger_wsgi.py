import sys
import os

# Ensure the working directory is set to the folder containing main.py
sys.path.insert(0, os.path.dirname(__file__))

# Import the app instance from your main.py
from main import app as application