import os
import shutil

def safe_cleanup():
    base_dir = r"d:\CLA\Clause-AI"
    
    print("Starting frontend cleanup...")
    
    frontend_path = os.path.join(base_dir, "frontend")
    
    if os.path.exists(frontend_path):
        try:
            shutil.rmtree(frontend_path)
            print(f"✅ Successfully removed entire frontend folder!")
        except Exception as e:
            print(f"❌ Could not remove frontend folder. Reason: File locked by your IDE or terminal.")
            print("\n⚠️ Please stop the 'streamlit run app.py' terminal and close any frontend files in your IDE, then run this again.")
    else:
        print("Frontend folder is already deleted.")

if __name__ == "__main__":
    safe_cleanup()
