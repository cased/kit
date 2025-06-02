import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
<<<<<<< Updated upstream
    sys.path.insert(0, str(ROOT))
=======
    sys.path.insert(0, str(ROOT)) 
>>>>>>> Stashed changes
