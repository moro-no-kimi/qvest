"""
Demo Runner for Reading Lift Pilot
Starts all components with proper setup
"""
import subprocess
import sys
import time
import os
import webbrowser
from pathlib import Path

def check_setup():
    """Check if setup has been run"""
    if not os.path.exists("data/library_data.db"):
        print("❌ Database not found. Please run setup first:")
        print("   python setup.py")
        return False
    return True

def start_api():
    """Start the FastAPI server"""
    print("🚀 Starting API server...")
    return subprocess.Popen([
        sys.executable, "api/main.py"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def start_streamlit_app(script_path, port):
    """Start a Streamlit app"""
    return subprocess.Popen([
        sys.executable, "-m", "streamlit", "run",
        script_path,
        "--server.port", str(port),
        "--server.headless", "true"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def main():
    """Main demo runner"""
    print("🎓 Fulton County Reading Lift Pilot - Demo Launcher")
    print("=" * 55)

    # Check if setup has been run
    if not check_setup():
        return 1

    processes = []

    try:
        # Start API server
        api_process = start_api()
        processes.append(("API Server", api_process))
        time.sleep(3)  # Give API time to start

        # Start Streamlit apps
        print("📚 Starting Student App...")
        student_process = start_streamlit_app("ui/student_app.py", 8501)
        processes.append(("Student App", student_process))

        print("👩‍🏫 Starting Librarian App...")
        librarian_process = start_streamlit_app("ui/librarian_app.py", 8502)
        processes.append(("Librarian App", librarian_process))

        print("📊 Starting District Dashboard...")
        dashboard_process = start_streamlit_app("ui/district_dashboard.py", 8503)
        processes.append(("District Dashboard", dashboard_process))

        # Wait for apps to start
        time.sleep(5)

        print("\n" + "=" * 55)
        print("✅ All services started successfully!")
        print("\n🌐 Access the applications:")
        print("   Student App:       http://localhost:8501")
        print("   Librarian App:     http://localhost:8502")
        print("   District Dashboard: http://localhost:8503")
        print("   API Documentation: http://localhost:8000/docs")
        print("\n💡 Demo Tips:")
        print("   • Student App: Try different demo students in sidebar")
        print("   • Librarian App: Review and approve recommendations")
        print("   • Dashboard: Monitor pilot metrics and trends")
        print("   • Press Ctrl+C to stop all services")

        # Optionally open browsers
        try:
            print("\n🖥️  Opening applications in browser...")
            time.sleep(2)
            webbrowser.open('http://localhost:8501')
            time.sleep(1)
            webbrowser.open('http://localhost:8502')
            time.sleep(1)
            webbrowser.open('http://localhost:8503')
        except:
            pass  # Browser opening is optional

        print("\n⏳ Services running... Press Ctrl+C to stop")

        # Keep running until interrupted
        try:
            while True:
                time.sleep(1)

                # Check if any process died
                for name, process in processes:
                    if process.poll() is not None:
                        print(f"\n❌ {name} stopped unexpectedly")

        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down services...")

    except Exception as e:
        print(f"❌ Error starting services: {e}")
        return 1

    finally:
        # Clean up processes
        for name, process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"   ✅ Stopped {name}")
            except:
                try:
                    process.kill()
                    print(f"   🔪 Killed {name}")
                except:
                    print(f"   ❌ Could not stop {name}")

        print("\n👋 Demo stopped. Thank you!")

    return 0

if __name__ == "__main__":
    sys.exit(main())