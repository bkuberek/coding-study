from coding_study.adapters.preferences_fs import FsPreferencesStore

PREFERENCES = ".cs/serve/preferences.json"
DOCUMENT = {"format": 1, "vim": True, "run_on_save": False, "typecheck": True}


def test_a_missing_file_reads_as_none(tmp_path):
    assert FsPreferencesStore(tmp_path).read() is None


def test_a_written_document_reads_back(tmp_path):
    store = FsPreferencesStore(tmp_path)
    store.write(DOCUMENT)
    assert store.read() == DOCUMENT


def test_the_document_is_one_line_of_json_in_the_serve_directory(tmp_path):
    FsPreferencesStore(tmp_path).write(DOCUMENT)
    assert (tmp_path / PREFERENCES).read_text() == (
        '{"format": 1, "vim": true, "run_on_save": false, "typecheck": true}\n'
    )


def test_writing_leaves_no_temporary_file(tmp_path):
    FsPreferencesStore(tmp_path).write(DOCUMENT)
    assert [path.name for path in (tmp_path / PREFERENCES).parent.iterdir()] == ["preferences.json"]


def test_a_file_that_is_not_json_reads_as_none(tmp_path):
    path = tmp_path / PREFERENCES
    path.parent.mkdir(parents=True)
    path.write_text("{vim: true")
    assert FsPreferencesStore(tmp_path).read() is None


def test_a_file_that_is_not_utf8_reads_as_none(tmp_path):
    path = tmp_path / PREFERENCES
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\xff\xfe{}")
    assert FsPreferencesStore(tmp_path).read() is None


def test_a_directory_in_place_of_the_file_reads_as_none(tmp_path):
    (tmp_path / PREFERENCES).mkdir(parents=True)
    assert FsPreferencesStore(tmp_path).read() is None
