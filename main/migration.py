from sqlalchemy import create_engine, inspect, text
from pathlib import Path


def run_migration():
    """
    Checks for and applies necessary schema changes to the database.
    """
    db_path = Path(__file__).parent / "videos.db"
    engine = create_engine(f"sqlite:///{db_path}")

    print("Running database migration check...")

    with engine.connect() as connection:
        inspector = inspect(engine)

        # --- Migration for transcript_processing.python_scrub_path ---
        table_name = "transcript_processing"
        column_name = "python_scrub_path"

        columns = [col["name"] for col in inspector.get_columns(table_name)]

        if column_name not in columns:
            print(f"Adding column '{column_name}' to table '{table_name}'...")
            try:
                # Use a transactional block
                with connection.begin():
                    connection.execute(
                        text(
                            f"ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR"
                        )
                    )
                print(f"Successfully added column '{column_name}'.")
            except Exception as e:
                print(f"Error adding column '{column_name}': {e}")
        else:
            print(
                f"Column '{column_name}' already exists in '{table_name}'. No migration needed."
            )


if __name__ == "__main__":
    run_migration()
