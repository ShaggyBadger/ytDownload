from desktop_connection_utility import run_remote_cmd
import db
from logger import setup_logger

logger = setup_logger(__name__)

REMOTE_PROJECT_DIR = "/home/alexander/pyProjects/sermonTranscriber"


def process_transcription():
    """
    Triggers the remote transcription process, handling existing processes.
    """
    db_session = db.SessionLocal()
    try:
        # Check if the remote process is already running
        check_cmd = "ps aux | grep '[c]ontroller.py'"
        logger.info(f"Checking for existing remote processes with: {check_cmd}")
        process_info = run_remote_cmd(check_cmd)

        if process_info:
            processes = [p for p in process_info.strip().split("\n") if p]
            num_processes = len(processes)

            if num_processes == 1:
                logger.warning(
                    "An instance of 'controller.py' is already running on the remote machine:"
                )
                logger.warning(process_info)
                logger.warning(
                    "Please wait for it to complete or manually stop it before starting a new process."
                )
                return

            elif num_processes > 1:
                logger.warning(
                    "Multiple instances of 'controller.py' are running on the remote machine:"
                )
                pids = []
                for i, process_line in enumerate(processes):
                    parts = process_line.split()
                    if len(parts) > 1:
                        pid = parts[1]
                        pids.append(pid)
                        logger.info(
                            f"{i + 1}: PID: {pid}, Details: {' '.join(parts[10:])}"
                        )

                while True:
                    try:
                        choice_str = input(
                            f"Enter the number of the process to KEEP (1-{num_processes}), or 'q' to quit: "
                        )
                        if choice_str.lower() == "q":
                            return
                        choice = int(choice_str)
                        if 1 <= choice <= num_processes:
                            break
                        else:
                            logger.warning(
                                f"Invalid choice. Please enter a number between 1 and {num_processes}."
                            )
                    except ValueError:
                        logger.warning("Invalid input. Please enter a number.")

                pid_to_keep = pids[choice - 1]
                pids_to_kill = [pid for pid in pids if pid != pid_to_keep]

                logger.info(f"Keeping process with PID: {pid_to_keep}")
                for pid in pids_to_kill:
                    kill_cmd = f"kill {pid}"
                    logger.info(f"Executing: {kill_cmd}")
                    run_remote_cmd(kill_cmd)

                logger.info("Cleanup complete. One instance remains.")
                return

        # If no processes are running, proceed to start a new one.
        # Check for videos ready for transcription
        videos_to_process = (
            db_session.query(db.Video)
            .filter(
                db.Video.stage_2_status == "completed",
                db.Video.stage_3_status.notin_(["complete", "completed", "processing"]),
            )
            .all()
        )

        if not videos_to_process:
            logger.info("No new videos ready for transcription.")
            return

        logger.info(f"Found {len(videos_to_process)} videos ready for transcription.")
        logger.info("Triggering remote processing...")

        remote_cmd = f"cd {REMOTE_PROJECT_DIR} && bash beginTranscription.sh"
        logger.info(f"Running remote command: {remote_cmd}")
        run_remote_cmd(remote_cmd)

        # Update the database
        for video in videos_to_process:
            video.stage_3_status = "processing"
        db_session.commit()

        logger.info(
            "Remote transcription process initiated successfully in the background."
        )
        logger.info(
            "You can monitor its progress via the 'controller.log' file on the remote machine."
        )

    finally:
        db_session.close()
