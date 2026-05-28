import os
import sys
import subprocess
import shutil

def run_build():
    print("=================================================================")
    print("    CONTENT STUDIO AI - PYINSTALLER COMPILATION ENGINE           ")
    print("=================================================================")
    
    # 1. Check virtual env python
    py_path = sys.executable
    print(f"[*] Running using Python: {py_path}")
    
    # 2. Check dependencies
    try:
        import PyInstaller
        print("[+] PyInstaller detected successfully.")
    except ImportError:
        print("[!] PyInstaller is not installed in current env. Installing...")
        subprocess.check_call([py_path, "-m", "pip", "install", "pyinstaller"])
    
    # 3. Clean previous builds
    print("[*] Cleaning up build artifacts...")
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"    Deleted {folder} folder.")
            
    spec_file = "Content_Studio_AI.spec"
    if not os.path.exists(spec_file):
        print(f"[!] Warning: {spec_file} spec file is missing!")
    
    pyinstaller_bin = "pyinstaller"
    venv_pyinstaller = os.path.join(".venv", "Scripts", "pyinstaller.exe")
    if os.path.exists(venv_pyinstaller):
        pyinstaller_bin = venv_pyinstaller
        print(f"[+] Found virtual environment PyInstaller: {pyinstaller_bin}")
    else:
        # Also check fallback locations
        fallback = os.path.join(os.path.dirname(sys.executable), "pyinstaller.exe")
        if os.path.exists(fallback):
            pyinstaller_bin = fallback
            print(f"[+] Found sibling PyInstaller binary: {pyinstaller_bin}")

    cmd = [
        pyinstaller_bin,
        "--clean",
        spec_file
    ]
    
    print(f"[*] Proposing build command: {' '.join(cmd)}")
    print("[*] Starting PyInstaller compilation process using custom spec file (this might take a few minutes)...")
    
    try:
        subprocess.check_call(cmd)
        print("=================================================================")
        print("[+] BUILD COMPLETED SUCCESSFULLY!")
        print("[+] Standalone executable created at: ./dist/Content_Studio_AI.exe")
        print("=================================================================")
    except Exception as e:
        print(f"[!] Compilation engine encountered an error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_build()
