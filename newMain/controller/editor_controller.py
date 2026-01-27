from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from sqlalchemy.orm import joinedload
from pathlib import Path
import json

from database.session_manager import get_session
from database.models import JobInfo, VideoInfo, JobStage, StageState
from services.editor import Editor
from config import config

class EditorMenu:
    def __init__(self):
        self.console = Console()
        self.options = {
            '1': {'desc': 'Build Paragraph JSON for single job', 'func': self._select_and_build_paragraph_json_for_single_job},
            '2': {'desc': 'Build Paragraph JSON for all eligible jobs', 'func': self._build_all_paragraph_jsons},
            '3': {'desc': 'Process Edited Paragraphs', 'func': self._run_paragraph_editing_menu}, # New option
            'b': {'desc': 'Back to Main Menu', 'func': None}
        }

    def _select_and_build_paragraph_json_for_single_job(self):
        """Allows user to select a single sermon and begin the process of building its paragraph JSON."""
        selected_job_data = self._get_selected_sermon_for_json_build()
        if selected_job_data:
            self.console.print(f"[cyan]Selected Job:[/cyan] {selected_job_data['job_ulid']} - [dim]{selected_job_data['title']}[/dim]")
            editor_service = Editor(job_id=selected_job_data['id'])
            editor_service.run_editor() # This method builds the JSON
        else:
            self.console.print("[yellow]No sermon selected for building paragraph JSON.[/yellow]")
        self.console.input("Press Enter to continue...")

    def _get_selected_sermon_for_json_build(self):
        """
        Displays a list of jobs that have completed the 'format_gemini' stage
        and allows the user to select one for building paragraph JSON.
        Returns a dictionary containing the selected job's information or None if no selection is made.
        """
        self.console.clear()
        self.console.rule("[bold blue]Select Sermon for Paragraph JSON Build[/bold blue]")

        jobs_for_editing = self._get_eligible_jobs_for_json_build()

        if not jobs_for_editing:
            self.console.print("[yellow]No sermons are currently eligible for paragraph JSON build.[/yellow]")
            self.console.print("[dim]A sermon must have successfully completed the 'format_gemini' stage and either have no paragraph JSON or the file is missing.[/dim]")
            return None

        table = Table(
            title="Available Sermons for Paragraph JSON Build",
            show_header=True,
            header_style="bold magenta",
            box=config.BOX_STYLE,
            padding=(0, 2)
        )
        table.add_column("No.", style="cyan", width=5)
        table.add_column("Job ULID", style="green")
        table.add_column("Title", style="green")
        table.add_column("Formatted Transcript Path", style="dim")

        job_map = {}
        for i, job_data in enumerate(jobs_for_editing):
            display_num = str(i + 1)
            job_map[display_num] = job_data
            table.add_row(
                display_num,
                job_data['job_ulid'],
                job_data['title'],
                job_data['output_path'] if job_data['output_path'] else "N/A"
            )
        
        self.console.print(table)
        
        while True:
            choice = Prompt.ask("[bold yellow]Select a sermon by number (or 'b' to go back)[/bold yellow]").strip().lower()
            if choice == 'b':
                return None
            
            selected_job_data = job_map.get(choice)
            if selected_job_data:
                return selected_job_data
            else:
                self.console.print("[red]Invalid selection. Please enter a valid number or 'b'.[/red]")

    def _get_eligible_jobs_for_json_build(self):
        """
        Queries the database for jobs that have successfully completed the 'format_gemini' stage
        and either have no paragraph JSON path or the file at that path does not exist.
        Returns a list of dictionaries, each containing relevant job information.
        """
        with get_session() as session:
            jobs_query_results = (
                session.query(
                    JobInfo.id.label('job_id'),
                    JobInfo.job_ulid.label('job_ulid'),
                    JobInfo.job_directory.label('job_directory'),
                    VideoInfo.title.label('title'),
                    JobStage.output_path.label('output_path'),
                    JobStage.paragraph_json_path.label('paragraph_json_path')
                )
                .join(VideoInfo, JobInfo.video_id == VideoInfo.id)
                .join(JobStage, JobInfo.id == JobStage.job_id)
                .filter(
                    JobStage.stage_name == "format_gemini",
                    JobStage.state == StageState.success,
                )
            ).all()

            jobs_list = []
            for job in jobs_query_results:
                paragraph_file_exists = False
                if job.paragraph_json_path:
                    paragraph_file_exists = Path(job.paragraph_json_path).exists()

                if job.paragraph_json_path is None or not paragraph_file_exists:
                    jobs_list.append({
                        'id': job.job_id,
                        'job_ulid': job.job_ulid,
                        'title': job.title,
                        'output_path': job.output_path,
                        'job_directory': job.job_directory
                    })
            return jobs_list

    def _build_all_paragraph_jsons(self):
        """
        Builds the paragraphs.json file for all jobs that are eligible
        (i.e., format_gemini stage is success and either have no paragraph JSON or the file is missing).
        """
        self.console.clear()
        self.console.rule("[bold blue]Building Paragraph JSONs for All Eligible Jobs[/bold blue]")

        eligible_jobs = self._get_eligible_jobs_for_json_build()

        if not eligible_jobs:
            self.console.print("[yellow]No eligible jobs found for building paragraph JSONs.[/yellow]")
            self.console.input("Press Enter to continue...")
            return

        self.console.print(f"[cyan]Found {len(eligible_jobs)} eligible jobs.[/cyan]")
        for i, job_data in enumerate(eligible_jobs):
            self.console.print(f"[bold white]Processing Job ({i+1}/{len(eligible_jobs)}):[/bold white] {job_data['job_ulid']} - {job_data['title']}")
            editor_service = Editor(job_id=job_data['id'])
            editor_service.run_editor()
            self.console.print() # Blank line for readability
        
        self.console.print("[green]Finished processing all eligible jobs.[/green]")
        self.console.input("Press Enter to continue...")

    # --- New methods for paragraph editing ---
    def _run_paragraph_editing_menu(self):
        """Displays and handles options for processing edited paragraphs (sending to Ollama)."""
        while True:
            self.console.clear()
            self.console.rule("[bold blue]Paragraph Editing Menu[/bold blue]")

            options = {
                '1': {'desc': 'Process a single job for editing', 'func': self._select_and_process_single_edited_job},
                '2': {'desc': 'Process all eligible jobs for editing', 'func': self._process_all_edited_jobs},
                'b': {'desc': 'Back to Editor Menu', 'func': None}
            }

            table = Table(
                title="Paragraph Editing Options",
                show_header=True,
                header_style="bold magenta",
                box=config.BOX_STYLE,
                padding=(0,2)
            )
            table.add_column("Option", style="cyan", width=8)
            table.add_column("Action", style="green")

            for key, val in options.items():
                table.add_row(key, val['desc'])

            self.console.print(table)

            choice = Prompt.ask("[bold yellow]Select an option[/bold yellow]").strip().lower()

            selected_option = options.get(choice)

            if selected_option is None:
                self.console.print("[red]Invalid choice. Please select a valid option.[/red]")
                self.console.input("Press Enter to continue...")
                continue

            action_func = selected_option.get('func')

            if action_func is None:
                break # Exit this secondary menu

            self.console.print(f"[cyan]Executing:[/cyan] {selected_option.get('desc')}")
            action_func()
        
        self.console.print("[bold green]Exiting Paragraph Editing Menu.[/bold green]")

    def _get_jobs_with_paragraphs_to_edit(self):
        """
        Queries the database for jobs that have a 'format_gemini' stage completed,
        have a paragraphs.json file, and still contain 'edited: None' entries within that file.
        Returns a list of dictionaries, each containing relevant job information.
        """
        with get_session() as session:
            jobs_query_results = (
                session.query(
                    JobInfo.id.label('job_id'),
                    JobInfo.job_ulid.label('job_ulid'),
                    JobInfo.job_directory.label('job_directory'),
                    VideoInfo.title.label('title'),
                    JobStage.paragraph_json_path.label('paragraph_json_path')
                )
                .join(VideoInfo, JobInfo.video_id == VideoInfo.id)
                .join(JobStage, JobInfo.id == JobStage.job_id)
                .filter(
                    JobStage.stage_name == "format_gemini",
                    JobStage.state == StageState.success,
                    JobStage.paragraph_json_path.isnot(None) # Must have a paragraph JSON path
                )
            ).all()

            jobs_list = []
            for job in jobs_query_results:
                paragraph_file_path = Path(job.paragraph_json_path)
                if not paragraph_file_path.exists():
                    # If the file path is in DB but file doesn't exist, it's eligible
                    self.console.print(f"[yellow]Warning: Paragraph JSON path in DB ({job.paragraph_json_path}) for job {job.job_ulid} does not exist on disk. It will be treated as eligible for re-processing.[/yellow]")
                    jobs_list.append({
                        'id': job.job_id,
                        'job_ulid': job.job_ulid,
                        'title': job.title,
                        'job_directory': job.job_directory,
                        'paragraph_json_path': job.paragraph_json_path # Keep this for display/info
                    })
                    continue # Move to next job

                try:
                    with open(paragraph_file_path, 'r') as f:
                        paragraphs_data = json.load(f)
                    
                    needs_editing = False
                    for entry in paragraphs_data:
                        if entry.get('edited') is None:
                            needs_editing = True
                            break
                    
                    if needs_editing:
                        jobs_list.append({
                            'id': job.job_id,
                            'job_ulid': job.job_ulid,
                            'title': job.title,
                            'job_directory': job.job_directory,
                            'paragraph_json_path': job.paragraph_json_path
                        })

                except json.JSONDecodeError as e:
                    self.console.print(f"[red]Error decoding JSON for job {job.job_ulid} at {paragraph_file_path}: {e}. Skipping.[/red]")
                except Exception as e:
                    self.console.print(f"[red]Error reading paragraph JSON for job {job.job_ulid} at {paragraph_file_path}: {e}. Skipping.[/red]")
            
            return jobs_list


    def _select_and_process_single_edited_job(self):
        """
        Allows the user to select a single job that has a paragraphs.json file
        with 'edited: None' entries and sends its paragraphs to Ollama for processing.
        """
        self.console.clear()
        self.console.rule("[bold blue]Select Sermon for Paragraph Editing[/bold blue]")

        jobs_to_edit = self._get_jobs_with_paragraphs_to_edit()

        if not jobs_to_edit:
            self.console.print("[yellow]No sermons found with paragraphs needing editing.[/yellow]")
            self.console.print("[dim]A sermon must have a created paragraph JSON file with unedited entries.[/dim]")
            self.console.input("Press Enter to continue...")
            return None

        table = Table(
            title="Available Sermons for Paragraph Editing",
            show_header=True,
            header_style="bold magenta",
            box=config.BOX_STYLE,
            padding=(0, 2)
        )
        table.add_column("No.", style="cyan", width=5)
        table.add_column("Job ULID", style="green")
        table.add_column("Title", style="green")
        table.add_column("Paragraph JSON Path", style="dim")

        job_map = {}
        for i, job_data in enumerate(jobs_to_edit):
            display_num = str(i + 1)
            job_map[display_num] = job_data
            table.add_row(
                display_num,
                job_data['job_ulid'],
                job_data['title'],
                job_data['paragraph_json_path'] if job_data['paragraph_json_path'] else "N/A"
            )
        
        self.console.print(table)
        
        while True:
            choice = Prompt.ask("[bold yellow]Select a sermon by number (or 'b' to go back)[/bold yellow]").strip().lower()
            if choice == 'b':
                return None
            
            selected_job_data = job_map.get(choice)
            if selected_job_data:
                self.console.print(f"[cyan]Selected Job:[/cyan] {selected_job_data['job_ulid']} - [dim]{selected_job_data['title']}[/dim]")
                editor_service = Editor(job_id=selected_job_data['id'])
                editor_service.process_paragraphs_for_editing()
                self.console.input("Press Enter to continue...")
                return
            else:
                self.console.print("[red]Invalid selection. Please enter a valid number or 'b'.[/red]")

    def _process_all_edited_jobs(self):
        """
        Iterates through all eligible jobs (those with paragraphs.json and
        'edited: None' entries) and sends their paragraphs to Ollama for processing.
        """
        self.console.clear()
        self.console.rule("[bold blue]Processing All Eligible Jobs for Paragraph Editing[/bold blue]")

        jobs_to_edit = self._get_jobs_with_paragraphs_to_edit()

        if not jobs_to_edit:
            self.console.print("[yellow]No jobs found with paragraphs needing editing.[/yellow]")
            self.console.input("Press Enter to continue...")
            return

        self.console.print(f"[cyan]Found {len(jobs_to_edit)} jobs with paragraphs to edit.[/cyan]")
        for i, job_data in enumerate(jobs_to_edit):
            self.console.print(f"[bold white]Processing Job ({i+1}/{len(jobs_to_edit)}):[/bold white] {job_data['job_ulid']} - {job_data['title']}")
            editor_service = Editor(job_id=job_data['id'])
            editor_service.process_paragraphs_for_editing()
            self.console.print() # Blank line for readability
        
        self.console.print("[green]Finished processing all eligible jobs.[/green]")
        self.console.input("Press Enter to continue...")


    def run(self):
        """
        Main entry point for the editor menu.
        """
        while True:
            self.console.clear()
            self.console.rule("[bold blue]Editor Menu[/bold blue]")

            table = Table(
                title="Editor Options",
                show_header=True,
                header_style="bold magenta",
                box=config.BOX_STYLE,
                padding=(0,2)
                )
            table.add_column("Option", style="cyan", width=8)
            table.add_column("Action", style="green")

            for key, val in self.options.items():
                table.add_row(key, val['desc'])

            self.console.print(table)

            choice = Prompt.ask("[bold yellow]Select an option[/bold yellow]").strip().lower()

            selected_option = self.options.get(choice)

            if selected_option is None:
                self.console.print("[red]Invalid choice. Please select a valid option.[/red]")
                self.console.input("Press Enter to continue...")
                continue

            action_func = selected_option.get('func')

            if action_func is None:
                break # Exit the menu

            self.console.print(f"[cyan]Executing:[/cyan] {selected_option.get('desc')}")
            action_func()
        
        self.console.print("[bold green]Exiting Editor Menu.[/bold green]")