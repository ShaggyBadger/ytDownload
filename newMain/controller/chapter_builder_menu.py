from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from sqlalchemy.orm import joinedload
from pathlib import Path
import json

from database.session_manager import get_session
from database.models import JobInfo, VideoInfo, JobStage, StageState
from services.chapter_builder import ChapterBuilder # This will be created next
from config import config

class ChapterBuilderMenu:
    def __init__(self):
        self.console = Console()
        self.options = {
            '1': {'desc': 'Build chapter for single job', 'func': self._select_and_build_single_chapter},
            '2': {'desc': 'Build chapter for all eligible jobs', 'func': self._build_all_chapters},
            'b': {'desc': 'Back to Main Menu', 'func': None}
        }

    def _get_eligible_jobs_for_chapter_build(self):
        """
        Queries the database for jobs that have successfully completed the 'edit_local_llm' stage,
        and either have no final document path or the file at that path does not exist.
        Returns a list of dictionaries, each containing relevant job information.
        """
        with get_session() as session:
            jobs_query_results = (
                session.query(
                    JobInfo.id.label('job_id'),
                    JobInfo.job_ulid.label('job_ulid'),
                    JobInfo.job_directory.label('job_directory'),
                    VideoInfo.title.label('title'),
                    JobStage.output_path.label('final_document_path') # This will be for the build_chapter stage
                )
                .join(VideoInfo, JobInfo.video_id == VideoInfo.id)
                .join(JobStage, JobInfo.id == JobStage.job_id)
                .filter(
                    JobStage.stage_name == "edit_local_llm", # Filter for completed editing
                    JobStage.state == StageState.success,
                )
            ).all()

            jobs_list = []
            for job in jobs_query_results:
                final_document_path = Path(job.job_directory) / config.FINAL_DOCUMENT_NAME
                
                # Check if the final document exists on disk
                final_document_exists = final_document_path.exists()

                # Include job if final document doesn't exist, regardless of DB output_path
                # The output_path in the query is actually for edit_local_llm, not build_chapter yet.
                # We'll rely on the file system check here.
                if not final_document_exists:
                    jobs_list.append({
                        'id': job.job_id,
                        'job_ulid': job.job_ulid,
                        'title': job.title,
                        'job_directory': job.job_directory,
                        'final_document_disk_path': str(final_document_path)
                    })
            return jobs_list

    def _select_and_build_single_chapter(self):
        """
        Allows the user to select a single job eligible for chapter building
        and triggers the chapter building process.
        """
        self.console.clear()
        self.console.rule("[bold blue]Select Sermon for Chapter Build[/bold blue]")

        jobs_to_build = self._get_eligible_jobs_for_chapter_build()

        if not jobs_to_build:
            self.console.print("[yellow]No sermons found eligible for chapter building.[/yellow]")
            self.console.print("[dim]A sermon must have completed the 'edit_local_llm' stage and not yet have a final document.[/dim]")
            self.console.input("Press Enter to continue...")
            return

        table = Table(
            title="Available Sermons for Chapter Building",
            show_header=True,
            header_style="bold magenta",
            box=config.BOX_STYLE,
            padding=(0, 2)
        )
        table.add_column("No.", style="cyan", width=5)
        table.add_column("Job ULID", style="green")
        table.add_column("Title", style="green")
        table.add_column("Final Document Path", style="dim")

        job_map = {}
        for i, job_data in enumerate(jobs_to_build):
            display_num = str(i + 1)
            job_map[display_num] = job_data
            table.add_row(
                display_num,
                job_data['job_ulid'],
                job_data['title'],
                job_data['final_document_disk_path']
            )
        
        self.console.print(table)
        
        while True:
            choice = Prompt.ask("[bold yellow]Select a sermon by number (or 'b' to go back)[/bold yellow]").strip().lower()
            if choice == 'b':
                return None
            
            selected_job_data = job_map.get(choice)
            if selected_job_data:
                self.console.print(f"[cyan]Selected Job:[/cyan] {selected_job_data['job_ulid']} - [dim]{selected_job_data['title']}[/dim]")
                chapter_builder_service = ChapterBuilder(job_id=selected_job_data['id'])
                chapter_builder_service.build_chapter_document()
                self.console.input("Press Enter to continue...")
                return
            else:
                self.console.print("[red]Invalid selection. Please enter a valid number or 'b'.[/red]")

    def _build_all_chapters(self):
        """
        Builds the final chapter document for all jobs eligible for chapter building.
        """
        self.console.clear()
        self.console.rule("[bold blue]Building Chapters for All Eligible Jobs[/bold blue]")

        jobs_to_build = self._get_eligible_jobs_for_chapter_build()

        if not jobs_to_build:
            self.console.print("[yellow]No eligible jobs found for chapter building.[/yellow]")
            self.console.input("Press Enter to continue...")
            return

        self.console.print(f"[cyan]Found {len(jobs_to_build)} eligible jobs.[/cyan]")
        for i, job_data in enumerate(jobs_to_build):
            self.console.print(f"[bold white]Processing Job ({i+1}/{len(jobs_to_build)}):[/bold white] {job_data['job_ulid']} - {job_data['title']}")
            chapter_builder_service = ChapterBuilder(job_id=job_data['id'])
            chapter_builder_service.build_chapter_document()
            self.console.print() # Blank line for readability
        
        self.console.print("[green]Finished processing all eligible jobs.[/green]")
        self.console.input("Press Enter to continue...")


    def run(self):
        """
        Main entry point for the chapter builder menu.
        """
        while True:
            self.console.clear()
            self.console.rule("[bold blue]Chapter Builder Menu[/bold blue]")

            table = Table(
                title="Chapter Builder Options",
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
        
        self.console.print("[bold green]Exiting Chapter Builder Menu.[/bold green]")