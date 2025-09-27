from pathlib import Path
import subprocess
import sys
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("plex_playlist_creator")


def resource_path(filename: str) -> str:
    """Get absolute path to resource, works for dev and PyInstaller bundle"""
    if hasattr(sys, "_MEIPASS"):  # PyInstaller extracts here
        return os.path.join(sys._MEIPASS, filename) # type: ignore
    return os.path.join(Path(__file__).parent , filename)

if __name__ == "__main__":
    target = resource_path("Entrypoint.py")
    logger.info(f"{target=}")
    try:
        process = subprocess.run(['streamlit','run', target])
    except KeyboardInterrupt:
        pass
    
    logger.info("All Done")
    sys.exit(0)

