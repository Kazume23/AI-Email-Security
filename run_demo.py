"""Run this file with the green Run button in PyCharm."""
import importlib.util
import subprocess
import sys
from pathlib import Path

if __name__ == '__main__':
    if importlib.util.find_spec('streamlit') is None:
        print('Brak Streamlit. W PyCharm otwórz requirements.txt i wybierz Install requirements.')
        sys.exit(1)
    app = Path(__file__).resolve().with_name('app.py')
    raise SystemExit(subprocess.call([sys.executable, '-m', 'streamlit', 'run', str(app),
                                     '--server.address=127.0.0.1', '--server.port=8501',
                                     '--server.maxUploadSize=5', '--browser.gatherUsageStats=false']))
