# remote_utils.py
import paramiko
from dotenv import load_dotenv
from pathlib import Path
import os

# Load environment variables from the .env file in the same directory (main/)
load_dotenv(dotenv_path=Path(__file__).resolve().parent / '.env')

SSH_HOST = os.getenv("SSH_HOST")
SSH_USER = os.getenv("SSH_USER")
SSH_PASSWORD = os.getenv("SSH_PASSWORD")
SSH_PORT = os.getenv("SSH_PORT")

# Validate that all required environment variables are present
required_vars = {"SSH_HOST": SSH_HOST, "SSH_USER": SSH_USER, "SSH_PASSWORD": SSH_PASSWORD, "SSH_PORT": SSH_PORT}
for var_name, var_value in required_vars.items():
    if not var_value:
        raise ValueError(f"Missing required environment variable: {var_name}")

def _make_client():
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    # AutoAddPolicy is insecure and should only be used for development.
    # In production, use RejectPolicy or WarningPolicy and pre-populate known_hosts.
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
            print(f"[stderr] {err}")
        return out
    finally:
        if client:
            client.close()


def create_remote_dir_if_not_exists(remote_path: str):
    """Creates a remote directory if it doesn't exist."""
    run_remote_cmd(f"mkdir -p {remote_path}")

def sftp_put(local_path: str, remote_path: str):
    client = None
    sftp = None
    try:
        client = _make_client()
        sftp = client.open_sftp()
        sftp.put(local_path, remote_path)
    finally:
        if sftp:
            sftp.close()
        if client:
            client.close()


def sftp_get(remote_path: str, local_path: str):
    client = None
    sftp = None
    try:
        client = _make_client()
        sftp = client.open_sftp()
        sftp.get(remote_path, local_path)
    finally:
        if sftp:
            sftp.close()
        if client:
            client.close()


if __name__ == "__main__":
    print("Attempting to connect and run 'hostname' command on desktop...")
    try:
        hostname = run_remote_cmd("hostname")
        print(f"Successfully connected. Desktop hostname: {hostname}")
    except Exception as e:
        print(f"Connection failed: {e}")
