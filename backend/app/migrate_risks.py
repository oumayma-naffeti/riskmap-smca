from sqlalchemy import inspect, text

from .database import engine


NEW_COLUMNS = {
    "code": "VARCHAR(20)",
    "name": "VARCHAR(200)",
    "category": "VARCHAR(50)",
    "causes": "TEXT",
    "consequence": "TEXT",
    "source": "VARCHAR(100)",
    "existing_measures": "TEXT",
    "owner": "VARCHAR(80)",
    "review_date": "DATE",
    "status": "VARCHAR(20) NOT NULL DEFAULT 'ouvert'",
}


def migrate():
    print("===== MIGRATION RISKS =====")

    with engine.begin() as connection:
        inspector = inspect(connection)

        if not inspector.has_table("risks"):
            raise RuntimeError("La table risks n'existe pas.")

        before_count = connection.execute(
            text("SELECT COUNT(*) FROM risks")
        ).scalar_one()

        existing_columns = {
            column["name"]
            for column in inspector.get_columns("risks")
        }

        print(f"Risques avant migration : {before_count}")

        for column_name, column_type in NEW_COLUMNS.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE risks ADD COLUMN {column_name} "
                        f"{column_type}"
                    )
                )
                print(f"[AJOUT] {column_name}")
            else:
                print(f"[EXISTANT] {column_name}")

        duplicates = connection.execute(
            text("""
                SELECT code, COUNT(*)
                FROM risks
                WHERE code IS NOT NULL
                GROUP BY code
                HAVING COUNT(*) > 1
            """)
        ).fetchall()

        if duplicates:
            raise RuntimeError(
                f"Codes de risques en double : {duplicates}"
            )

        connection.execute(
            text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ix_risks_code
                ON risks (code)
            """)
        )

        after_count = connection.execute(
            text("SELECT COUNT(*) FROM risks")
        ).scalar_one()

        if before_count != after_count:
            raise RuntimeError(
                "Le nombre de risques a changé pendant la migration."
            )

        statuses = connection.execute(
            text("""
                SELECT status, COUNT(*)
                FROM risks
                GROUP BY status
                ORDER BY status
            """)
        ).fetchall()

        print(f"Risques après migration : {after_count}")
        print("Répartition des statuts :")

        for status, count in statuses:
            print(f"  {status}: {count}")

    print("===== MIGRATION TERMINEE AVEC SUCCES =====")


if __name__ == "__main__":
    migrate()
