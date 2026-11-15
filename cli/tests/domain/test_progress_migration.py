"""The line that says what migrating progress.db did
(docs/specs/compatibility.md#migrations)."""

from coding_study.domain.errors import BackupError, MigrationError
from coding_study.domain.progress_migration import ProgressMigration


def test_a_migration_with_a_backup_names_it():
    migration = ProgressMigration(4, 7, ".cs/backups/progress-schema-4-20261114T101500Z.db")
    assert migration.notice == (
        "progress.db: backed up to .cs/backups/progress-schema-4-20261114T101500Z.db; "
        "migrated from schema 4 to 7"
    )


def test_a_migration_of_a_new_database_has_no_backup_to_name():
    assert ProgressMigration(0, 7, None).notice == "progress.db: migrated from schema 0 to 7"


def test_a_failed_backup_says_nothing_changed():
    assert str(BackupError("permission denied")) == (
        "cannot back up progress.db before migrating it: permission denied; nothing changed"
    )


def test_a_failed_migration_names_the_backup_it_restored():
    error = MigrationError(3, 5, "no such table: scores", ".cs/backups/progress-schema-3-x.db")
    assert str(error) == (
        "migrating progress.db from schema 3 failed at schema 5: no such table: scores; "
        "restored it from .cs/backups/progress-schema-3-x.db"
    )


def test_a_failed_migration_with_a_failed_restore_names_the_copy_to_put_back():
    error = MigrationError(
        3, 5, "no such table: scores", ".cs/backups/progress-schema-3-x.db", "disk I/O error"
    )
    assert str(error) == (
        "migrating progress.db from schema 3 failed at schema 5: no such table: scores, "
        "and restoring it failed: disk I/O error; copy .cs/backups/progress-schema-3-x.db "
        "over progress.db"
    )
