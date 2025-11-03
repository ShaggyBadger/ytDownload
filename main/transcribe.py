from desktop_connection_utility import run_remote_cmd
import db

REMOTE_PROJECT_DIR = "/home/alexander/pyProjects/sermonTranscriber"

def process_transcription():
    """
    Triggers the remote transcription process, handling existing processes.
    """
    db_session = db.SessionLocal()
    try:
        # Check if the remote process is already running
        check_cmd = "ps aux | grep '[c]ontroller.py'"
        print(f"Checking for existing remote processes with: {check_cmd}")
        process_info = run_remote_cmd(check_cmd)

        if process_info:
            processes = [p for p in process_info.strip().split('\n') if p]
            num_processes = len(processes)

            if num_processes == 1:
                print("\nAn instance of 'controller.py' is already running on the remote machine:")
                print(process_info)
                print("Please wait for it to complete or manually stop it before starting a new process.")
                return

            elif num_processes > 1:
                print("\nMultiple instances of 'controller.py' are running on the remote machine:")
                pids = []
                for i, process_line in enumerate(processes):
                    parts = process_line.split()
                    if len(parts) > 1:
                        pid = parts[1]
                        pids.append(pid)
                        print(f"{i + 1}: PID: {pid}, Details: {' '.join(parts[10:])}")

                while True:
                    try:
                        choice_str = input(f"Enter the number of the process to KEEP (1-{num_processes}), or 'q' to quit: ")
                        if choice_str.lower() == 'q':
                            return
                        choice = int(choice_str)
                        if 1 <= choice <= num_processes:
                            break
                        else:
                            print(f"Invalid choice. Please enter a number between 1 and {num_processes}.")
                    except ValueError:
                        print("Invalid input. Please enter a number.")

                pid_to_keep = pids[choice - 1]
                pids_to_kill = [pid for pid in pids if pid != pid_to_keep]

                print(f"\nKeeping process with PID: {pid_to_keep}")
                for pid in pids_to_kill:
                    kill_cmd = f"kill {pid}"
                    print(f"Executing: {kill_cmd}")
                    run_remote_cmd(kill_cmd)
                
                print("\nCleanup complete. One instance remains.")
                return

        # If no processes are running, proceed to start a new one.
        # Check for videos ready for transcription
        videos_to_process = db_session.query(db.Video).filter(
            db.Video.stage_2_status == "completed",
            db.Video.stage_3_status.notin_(["complete", "completed", "processing"])
        ).all()

        if not videos_to_process:
            print("\nNo new videos ready for transcription.")
            return

        print(f"\nFound {len(videos_to_process)} videos ready for transcription.")
        print("Triggering remote processing...")

        # Command to start the transcription process in the background
        remote_cmd = (
            f"cd {REMOTE_PROJECT_DIR}/main && "
            f"source ../venvFiles39/bin/activate && "
            f"nohup python3 controller.py > ../controller.log 2>&1 &"
        )
        print(f"Running remote command: {remote_cmd}")
        run_remote_cmd(remote_cmd)

        # Update the database
        for video in videos_to_process:
            video.stage_3_status = "processing"
        db_session.commit()

        print("\nRemote transcription process initiated successfully in the background.")
        print("You can monitor its progress via the 'controller.log' file on the remote machine.")

    finally:
        db_session.close()
