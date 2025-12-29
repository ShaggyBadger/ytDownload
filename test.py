import subprocess
import time
import requests
import os
from dotenv import load_dotenv
from pathlib import Path
import paramiko # Added for SSH client

# Load environment variables
# Assumes .env file is in the 'main' directory
load_dotenv(Path(__file__).resolve().parent / "main/.env")

SSH_HOST = os.getenv("SSH_HOST")
SSH_USER = os.getenv("SSH_USER")
SSH_PASSWORD = os.getenv("SSH_PASSWORD") # Keep if needed for paramiko, but SSH command will use keys
SSH_PORT = os.getenv("SSH_PORT")

# --- Paramiko helper functions (copied from main/desktop_connection_utility.py) ---
def _make_client():
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    client.connect(
        hostname=SSH_HOST,
        username=SSH_USER,
        password=SSH_PASSWORD,
        port=int(SSH_PORT),
        allow_agent=False,
        look_for_keys=False,
        timeout=10,
    )
    return client

def run_remote_cmd(cmd: str):
    client = None
    try:
        client = _make_client()
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if err:
            print(f"[stderr from remote cmd] {err}")
        return out
    finally:
        if client:
            client.close()
# --- End of Paramiko helper functions ---


class SSHTunnel:
    """A context manager for creating and managing an SSH tunnel."""
    def __init__(self, remote_host, remote_user, remote_port, local_port, remote_bind_host, remote_bind_port):
        self.remote_host = remote_host
        self.remote_user = remote_user
        self.remote_port = remote_port
        self.local_port = local_port
        self.remote_bind_host = remote_bind_host
        self.remote_bind_port = remote_bind_port
        self.tunnel_process = None

    def __enter__(self):
        print("Starting SSH tunnel...")
        cmd = [
            "ssh",
            "-N",  # Do not execute a remote command
            f"-L", f"{self.local_port}:{self.remote_bind_host}:{self.remote_bind_port}",
            f"{self.remote_user}@{self.remote_host}",
            "-p", str(self.remote_port),
        ]
        
        # Using Popen to run the command in the background
        self.tunnel_process = subprocess.Popen(cmd)
        
        # Give the tunnel a moment to establish
        time.sleep(2) 
        
        # Check if the process started successfully
        if self.tunnel_process.poll() is not None:
            raise RuntimeError("SSH tunnel failed to start. Check your SSH credentials and connection.")
            
        print(f"SSH tunnel established. Local port {self.local_port} is forwarded to {self.remote_bind_host}:{self.remote_bind_port} on {self.remote_host}.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.tunnel_process:
            print("Closing SSH tunnel...")
            self.tunnel_process.terminate()
            self.tunnel_process.wait()
            print("SSH tunnel closed.")

def main():
    """
    Main function to create a tunnel and query the remote Ollama service.
    """
    if not all([SSH_HOST, SSH_USER, SSH_PORT]):
        print("Error: Please make sure SSH_HOST, SSH_USER, and SSH_PORT are set in your .env file.")
        return

    try:
        print(f"Attempting to get WSL IP from remote host '{SSH_HOST}'...")
        # Get WSL IP from the remote Windows machine by executing the command via its full path
        wsl_ip_output = run_remote_cmd("/mnt/c/Windows/System32/wsl.exe hostname -I")
        wsl_ip = wsl_ip_output.split()[0] if wsl_ip_output else None
        if not wsl_ip:
            raise ValueError("Could not determine WSL IP address. Is WSL running and `wsl hostname -I` working on the remote machine?")
        print(f"Detected WSL IP: {wsl_ip}")

        ollama_port = 11434
        local_forward_port = 11434

        with SSHTunnel(
            remote_host=SSH_HOST,
            remote_user=SSH_USER,
            remote_port=int(SSH_PORT),
            local_port=local_forward_port,
            remote_bind_host=wsl_ip, # Use the dynamic WSL IP here
            remote_bind_port=ollama_port
        ):
            print("\nAttempting to contact Ollama through the tunnel...")
            try:
                resp = requests.post(
                    f"http://localhost:{local_forward_port}/api/generate",
                    json={
                        "model": "llama3.1:8b",
                        "prompt": "Why is the sky blue?",
                        "stream": False
                    },
                    timeout=120
                )
                resp.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

                print("Response status:", resp.status_code)
                response_data = resp.json()
                print("Ollama response:", response_data.get("response", "No response text found."))

            except requests.exceptions.RequestException as e:
                print(f"\nError communicating with Ollama: {e}")
                print("Please check the following:")
                print(f"1. Is the Ollama service running INSIDE WSL on the remote machine ('{SSH_HOST}')?")
                print(f"2. Is it accessible on {wsl_ip}:{ollama_port} *from INSIDE WSL itself*?")
                print("3. Do you have the 'llama3.1:8b' model installed on the remote Ollama instance? (`ollama list` inside WSL)")
                print("4. Is `ssh` working correctly from your local machine to the remote Windows machine?")
                print("5. Is `wsl hostname -I` working correctly on the remote Windows machine and returning the WSL IP?")


    except (RuntimeError, ValueError, paramiko.SSHException, Exception) as e:
        print(f"\nAn error occurred during tunnel setup or WSL IP retrieval: {e}")

if __name__ == "__main__":
    main()

