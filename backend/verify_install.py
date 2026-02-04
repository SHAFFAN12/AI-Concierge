
import sys

packages = [
    "fastapi",
    "uvicorn",
    "pydantic",
    "pymongo", 
    "sentence_transformers"
]

print("Verifying installation...")
for package in packages:
    try:
        __import__(package)
        print(f"[OK] {package}")
    except ImportError as e:
        print(f"[FAIL] {package}: {e}")
