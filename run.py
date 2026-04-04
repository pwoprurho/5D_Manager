import subprocess
import sys

if __name__ == "__main__":
    print("Starting 5D Project Management Server on http://127.0.0.1:8000...")
    # Run the uvicorn executable directly using a subprocess to avoid PATH/Module conflicts
    try:
        subprocess.run(["uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"])
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"Error starting server: {e}")

