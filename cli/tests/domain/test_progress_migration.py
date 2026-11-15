"""The line that says what migrating progress.db did
(docs/specs/compatibility.md#migrations)."""

from coding_study.domain.errors import BackupError
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
