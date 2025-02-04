import os
import subprocess

def install_faiss():
    try:
        # Install condacolab silently
        subprocess.run(["pip", "install", "-q", "condacolab"], check=True)

        # Import and install Conda
        import condacolab
        condacolab.install()

        # Install faiss-gpu using mamba
        os.system("mamba install -q -y -c pytorch faiss-gpu")

        print("✅ faiss-gpu installed successfully!")
    except Exception as e:
        print(f"❌ Installation failed: {e}")


install_faiss()
