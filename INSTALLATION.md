# ⚙️ Installation Guide

> Tested on **Python 3.11+** (recommended: 3.12).  
> Follow the steps below to set up, run, and document the project on any OS.

---

## 🧩 Setup

### 🪟 Windows (PowerShell)
```powershell
# 1️⃣ Clone the repository
git clone https://github.com/TaylorBrown96/SE25Fall.git
cd SE25Fall/proj2

# 2️⃣ Create and activate a virtual environment
py -3 -m venv .venv
. .\.venv\Scripts\Activate.ps1
# If activation is blocked:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 3️⃣ Install dependencies
python -m pip install --upgrade pip
pip install -r proj2/requirements.txt
```

### 🐧MacOS / Linux (Bash/Zsh)
```bash
# 1️⃣ Clone the repository
git clone https://github.com/TaylorBrown96/SE25Fall.git
cd SE25Fall/proj2

# 2️⃣ Create & activate a venv
python3 -m venv .venv
source .venv/bin/activate

# 3️⃣ Install packages
python -m pip install --upgrade pip
pip install -r proj2/requirements.txt
```

---

## 🚀Usage

### Running the Application
Once dependencies are installed and the virtual environment is activated, you can run the Flask server:

### 🪟Windows (PowerShell)
```powershell
# Start the development server
flask run
```

### 🐧MacOS / Linux (Bash/Zsh)
```bash
# Start the development server
flask run
```

---

## 🧪Running Tests
Execute unit tests using pytest:
```bash
# For full information run:
pytest
# Add a '-q'(quiet) flag to show concise, easy-to-read output (dots for passes, 'F' for failures):
pytest -q
```

---

## 📚Documentation

### _Documentation is generated using pdoc._
Documentation is automatically generated using pdoc and deployed to GitHub Pages whenever new changes are merged into the `main` branch.

### 🧩 Automated Docs
* CI/CD workflow (`docs.yml`) builds and publishes docs from `proj2/` to the `gh-pages` branch.

* Live documentation becomes available at the GitHub Pages link after each successful merge.

* Source code is hidden; only public functions, classes, and docstrings are shown.

### 🖥️ Build Docs Locally
You can also generate and preview the documentation manually:
### 🪟Windows (PowerShell)
```powershell
# Temporarily add current directory to Python path
$env:PYTHONPATH="." ;
pdoc proj2 --no-show-source --template-dir proj2\pdoc_templates -o proj2\site
python .\scripts\build_docs.py
# View the documentation in your default browser
start proj2\site\index.html
```

### 🐧MacOS / Linux (Bash/Zsh)
```bash
# Temporarily add current directory to Python path
export PYTHONPATH="."
pdoc proj2 --no-show-source --template-dir proj2/pdoc_templates -o proj2/site
python ./scripts/build_docs.py
# View the documentation in your default browser
open proj2/site/index.html
```

The generated HTML files will be available in the `proj2/site` directory.