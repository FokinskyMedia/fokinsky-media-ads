@echo off
if exist venv\Scripts\activate.bat (
  call venv\Scripts\activate.bat
)
python - <<'PY'
import sys, subprocess, pkgutil
reqs = ["flask","flask_sqlalchemy","flask_wtf"]
for r in reqs:
    if pkgutil.find_loader(r) is None:
        subprocess.check_call([sys.executable, "-m", "pip", "install", r])
print("Deps checked")
PY
echo Starting Fokinsky Media & Ads...
python app.py
