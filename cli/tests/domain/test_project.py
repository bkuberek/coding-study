"""The `project` block of meta.yaml and the paths inside a project folder."""

import re
from dataclasses import replace

import pytest

from coding_study.domain.problem import Language
from coding_study.domain.project import (
    DEFAULT_TESTS_DIRECTORY,
    PROJECT_LANGUAGES,
    Project,
    ProjectFile,
    ProjectTree,
    entry_files,
    entry_issue,
    level_methods,
    level_test_file,
    level_test_pattern,
    level_tests_directory_issue,
    method_text,
    project_language,
    project_tests_package,
    relative_path_issue,
)
from tests.project_builders import BANK, CREATE_ACCOUNT, DEPOSIT, TRANSFER, method, project_meta

JVM = (Language.JAVA, Language.KOTLIN)


def test_project_problems_exist_in_every_language():
    assert PROJECT_LANGUAGES == (
        Language.PYTHON,
        Language.TYPESCRIPT,
        Language.JAVA,
        Language.KOTLIN,
        Language.GO,
        Language.RUST,
    )


def test_generated_tests_go_to_tests_by_default():
    assert Project("bank.bank").tests == DEFAULT_TESTS_DIRECTORY == "tests"


# relative paths


@pytest.mark.parametrize(
    "path", ["README.md", "bank/bank.py", "src/bank.ts", ".vscode/settings.json", "a..b/c"]
)
def test_a_path_inside_its_folder_is_valid(path):
    assert relative_path_issue(path) is None


@pytest.mark.parametrize(
    ("path", "issue"),
    [
        ("", "is empty"),
        ("/etc/passwd", "is absolute"),
        ("../bank.py", 'leaves its folder through ".."'),
        ("bank/../../bank.py", 'leaves its folder through ".."'),
        ("bank/..", 'leaves its folder through ".."'),
        ("bank//bank.py", 'has an empty or "." segment'),
        ("./bank.py", 'has an empty or "." segment'),
        ("bank/", 'has an empty or "." segment'),
        ("bank\\bank.py", "uses \\ instead of /"),
    ],
    ids=["empty", "absolute", "up", "up twice", "up at the end", "empty", "dot", "trailing", "\\"],
)
def test_a_path_that_could_leave_its_folder_is_rejected(path, issue):
    assert relative_path_issue(path) == issue


# entry


@pytest.mark.parametrize("entry", ["bank", "bank.bank", "bank_app.core.bank", "_bank", "bank.py"])
def test_a_python_entry_is_a_dotted_module(entry):
    assert entry_issue(entry, Language.PYTHON) is None


@pytest.mark.parametrize(
    "entry", ["bank/bank", "bank..bank", ".bank", "bank.", "1bank", "bank.class", "bank-app", ""]
)
def test_a_python_entry_that_is_not_a_dotted_module_is_rejected(entry):
    assert entry_issue(entry, Language.PYTHON) == (
        f'"{entry}" is not a dotted module name such as bank.bank'
    )


@pytest.mark.parametrize("entry", ["src/bank.ts", "bank.ts"])
def test_a_typescript_entry_is_a_ts_file(entry):
    assert entry_issue(entry, Language.TYPESCRIPT) is None


@pytest.mark.parametrize(
    "entry", ["src/bank.js", "src/bank", "/src/bank.ts", "../bank.ts", "src//bank.ts", "bank.bank"]
)
def test_a_typescript_entry_that_is_not_a_ts_file_in_the_project_is_rejected(entry):
    assert entry_issue(entry, Language.TYPESCRIPT) == (
        f'"{entry}" is not a .ts file inside the project such as src/bank.ts'
    )


@pytest.mark.parametrize("entry", ["bank.go", "bank/bank.go", "internal/core/bank.go"])
def test_a_go_entry_is_a_go_file(entry):
    assert entry_issue(entry, Language.GO) is None


@pytest.mark.parametrize(
    "entry", ["bank_test.go", "bank/bank_test.go", "bank", "bank.ts", "../bank.go", "/bank.go"]
)
def test_a_go_entry_that_is_not_a_go_file_in_the_project_is_rejected(entry):
    assert entry_issue(entry, Language.GO) == (
        f'"{entry}" is not a .go file inside the project such as bank.go, other than a test file'
    )


def test_a_go_entry_is_its_own_file():
    assert entry_files("bank/bank.go", Language.GO) == ("bank/bank.go",)


@pytest.mark.parametrize("language", JVM)
@pytest.mark.parametrize("entry", ["bank.Bank", "com.example.bank.Bank", "bank_app.Bank", "b.B"])
def test_a_jvm_entry_is_a_class_in_a_named_package(entry, language):
    assert entry_issue(entry, language) is None


@pytest.mark.parametrize("language", JVM)
@pytest.mark.parametrize(
    "entry",
    ["Bank", "bank/Bank", "bank..Bank", ".Bank", "bank.", "bank.1Bank", "bank-app.Bank", ""],
)
def test_a_jvm_entry_that_is_not_a_class_in_a_package_is_rejected(entry, language):
    assert entry_issue(entry, language) == (
        f'"{entry}" is not the fully qualified name of a class in a package, such as bank.Bank'
    )


@pytest.mark.parametrize("language", JVM)
@pytest.mark.parametrize("entry", ["bank.class.Bank", "object.Bank", "bank.fun.Bank"])
def test_a_jvm_entry_names_no_keyword_of_java_or_kotlin(entry, language):
    keyword = entry.split(".")[-2]
    assert entry_issue(entry, language) == f'"{entry}" holds the keyword "{keyword}"'


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (Language.JAVA, ("src/main/java/com/bank/Bank.java",)),
        (Language.KOTLIN, ("src/main/kotlin/com/bank/Bank.kt",)),
    ],
)
def test_a_jvm_entry_is_the_source_file_of_its_class(language, expected):
    assert entry_files("com.bank.Bank", language) == expected


@pytest.mark.parametrize("entry", ["bank", "bank_app", "b2", "my_bank_3"])
def test_a_rust_entry_is_a_crate_name(entry):
    assert entry_issue(entry, Language.RUST) is None


@pytest.mark.parametrize(
    "entry", ["bank-app", "Bank", "_bank", "1bank", "bank.rs", "src/lib.rs", "bank::Bank", ""]
)
def test_a_rust_entry_that_is_not_a_crate_name_is_rejected(entry):
    assert entry_issue(entry, Language.RUST) == (
        f'"{entry}" is not a crate name such as bank: lowercase letters, digits and _'
    )


@pytest.mark.parametrize("entry", ["fn", "loop", "type", "self", "crate"])
def test_a_rust_entry_that_is_a_keyword_is_rejected(entry):
    assert entry_issue(entry, Language.RUST) == f'"{entry}" is a Rust keyword'


@pytest.mark.parametrize("entry", ["std", "core", "test", "user", "cs_runner", "rust_decimal"])
def test_a_rust_entry_that_names_a_crate_of_the_build_is_rejected(entry):
    assert entry_issue(entry, Language.RUST) == (
        f'"{entry}" is a crate the build or the tests already name'
    )


def test_a_rust_entry_is_the_library_root_of_its_crate():
    assert entry_files("bank", Language.RUST) == ("src/lib.rs",)


def test_a_python_entry_is_a_module_file_or_a_package():
    assert entry_files("bank.bank", Language.PYTHON) == ("bank/bank.py", "bank/bank/__init__.py")


def test_a_typescript_entry_is_its_own_file():
    assert entry_files("src/bank.ts", Language.TYPESCRIPT) == ("src/bank.ts",)


# generated tests


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (Language.PYTHON, "tests/test_level_2.py"),
        (Language.TYPESCRIPT, "tests/level-2.test.ts"),
        (Language.GO, "tests/level_2_test.go"),
        (Language.RUST, "tests/level_2.rs"),
    ],
)
def test_each_level_has_one_generated_test_file(language, expected):
    assert level_test_file(Project("bank.bank"), language, 2) == expected


@pytest.mark.parametrize(
    ("language", "tests", "expected"),
    [
        (Language.JAVA, "src/test/java/bank", "src/test/java/bank/Level2Test.java"),
        (Language.KOTLIN, "src/test/kotlin/bank", "src/test/kotlin/bank/Level2Test.kt"),
    ],
)
def test_a_jvm_level_is_a_test_class_in_the_tests_package(language, tests, expected):
    assert level_test_file(Project("bank.Bank", tests), language, 2) == expected


def test_generated_test_files_go_to_the_project_tests_directory():
    project = Project("bank.bank", "checks/levels")
    assert level_test_file(project, Language.PYTHON, 1) == "checks/levels/test_level_1.py"


def test_rust_tests_go_to_tests():
    assert level_tests_directory_issue("tests", Language.RUST) is None


def test_rust_tests_anywhere_else_are_rejected():
    assert level_tests_directory_issue("checks", Language.RUST) == (
        '"checks" is not tests, where Cargo finds integration tests'
    )


@pytest.mark.parametrize(
    ("language", "name"),
    [
        (Language.PYTHON, "test_level_12.py"),
        (Language.TYPESCRIPT, "level-3.test.ts"),
        (Language.GO, "level_7_test.go"),
        (Language.JAVA, "Level12Test.java"),
        (Language.KOTLIN, "Level3Test.kt"),
        (Language.RUST, "level_4.rs"),
    ],
)
def test_the_level_test_pattern_matches_a_generated_file_of_any_level(language, name):
    assert level_test_pattern(language).fullmatch(name)


@pytest.mark.parametrize(
    "name", ["test_level_0.py", "test_level_x.py", "test_level_1.pyc", "level-1.test.ts"]
)
def test_the_level_test_pattern_matches_nothing_else(name):
    assert level_test_pattern(Language.PYTHON).fullmatch(name) is None


@pytest.mark.parametrize("name", ["level_0_test.go", "level_1.go", "level_1_test.go.orig"])
def test_the_go_level_test_pattern_matches_nothing_else(name):
    assert level_test_pattern(Language.GO).fullmatch(name) is None


# the generated tests' directory


@pytest.mark.parametrize("tests", ["tests", "checks/levels", "level_tests"])
def test_a_go_tests_directory_ends_in_a_package_name(tests):
    assert level_tests_directory_issue(tests, Language.GO) is None


@pytest.mark.parametrize("tests", ["level-tests", "checks/2", "tests/func"])
def test_a_go_tests_directory_that_cannot_name_a_package_is_rejected(tests):
    assert level_tests_directory_issue(tests, Language.GO) == (
        f'"{tests}" does not end in a Go package name such as tests'
    )


@pytest.mark.parametrize("language", [Language.PYTHON, Language.TYPESCRIPT])
def test_other_languages_take_any_tests_directory(language):
    assert level_tests_directory_issue("level-tests", language) is None


@pytest.mark.parametrize(
    "name", ["Level0Test.java", "Level1Tests.java", "Level1Test.kt", "level1Test.java"]
)
def test_the_java_level_test_pattern_matches_nothing_else(name):
    assert level_test_pattern(Language.JAVA).fullmatch(name) is None


@pytest.mark.parametrize(
    ("language", "tests"),
    [(Language.JAVA, "src/test/java/bank"), (Language.KOTLIN, "src/test/kotlin/com/bank")],
)
def test_a_jvm_tests_directory_is_a_package_of_the_test_sources(language, tests):
    assert level_tests_directory_issue(tests, language) is None


@pytest.mark.parametrize(
    ("language", "tests"),
    [
        (Language.JAVA, "tests"),
        (Language.JAVA, "src/test/java"),
        (Language.JAVA, "src/test/kotlin/bank"),
        (Language.JAVA, "src/test/java/bank-app"),
        (Language.JAVA, "src/test/java/bank/class"),
        (Language.KOTLIN, "src/test/java/bank"),
    ],
)
def test_a_jvm_tests_directory_outside_a_test_package_is_rejected(language, tests):
    root = "src/test/java" if language is Language.JAVA else "src/test/kotlin"
    assert level_tests_directory_issue(tests, language) == (
        f'"{tests}" is not a package directory under {root}/, such as {root}/bank'
    )


@pytest.mark.parametrize(
    ("language", "tests"),
    [(Language.JAVA, "src/test/java/com/bank"), (Language.KOTLIN, "src/test/kotlin/com/bank")],
)
def test_jvm_tests_are_in_the_package_their_directory_names(language, tests):
    assert project_tests_package(Project("com.bank.Bank", tests), language) == "com.bank"


# the problem's language


def test_a_project_problem_is_solved_in_its_one_language():
    assert project_language(project_meta(language=Language.TYPESCRIPT)) is Language.TYPESCRIPT


def test_a_project_problem_with_two_languages_has_no_language_of_its_own():
    meta = replace(project_meta(), languages=(Language.PYTHON, Language.TYPESCRIPT))
    with pytest.raises(ValueError, match="bank-project-python lists 2 languages, not one"):
        project_language(meta)


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (Language.PYTHON, "create_account(timestamp: int, account_id: str) -> bool"),
        (Language.TYPESCRIPT, "createAccount(timestamp: number, accountId: string): boolean"),
        (Language.GO, "CreateAccount(timestamp int64, accountId string) bool"),
        (Language.JAVA, "boolean createAccount(long timestamp, String accountId)"),
        (Language.KOTLIN, "createAccount(timestamp: Long, accountId: String): Boolean"),
        (Language.RUST, "create_account(&mut self, timestamp: i64, account_id: String) -> bool"),
    ],
)
def test_a_method_reads_as_its_language_declares_it(language, expected):
    assert method_text(CREATE_ACCOUNT, language) == expected


@pytest.mark.parametrize(
    ("returns", "python", "typescript"),
    [
        ("void", "None", "void"),
        ("double", "float", "number"),
        ("char", "str", "string"),
        ("decimal", "Decimal", "Decimal"),
        ("date", "date", "string"),
        ("list<string>", "list[str]", "string[]"),
        ("int[][]", "list[list[int]]", "number[][]"),
    ],
)
def test_a_method_spells_its_types_in_its_language(returns, python, typescript):
    found = method("snapshot", 1, returns=returns)
    texts = (method_text(found, Language.PYTHON), method_text(found, Language.TYPESCRIPT))
    assert texts == (f"snapshot() -> {python}", f"snapshot(): {typescript}")


@pytest.mark.parametrize(
    ("returns", "go"),
    [
        ("double", "float64"),
        ("char", "rune"),
        ("decimal", "decimal.Decimal"),
        ("date", "time.Time"),
        ("list<string>", "[]string"),
        ("int[][]", "[][]int"),
    ],
)
def test_a_go_method_spells_its_types_in_go(returns, go):
    assert method_text(method("snapshot", 1, returns=returns), Language.GO) == f"Snapshot() {go}"


def test_a_go_method_without_a_result_has_no_return_type():
    assert method_text(method("reset", 1, returns="void"), Language.GO) == "Reset()"


@pytest.mark.parametrize(
    ("returns", "java", "kotlin"),
    [
        ("double", "double", "Double"),
        ("char", "char", "Char"),
        ("decimal", "BigDecimal", "BigDecimal"),
        ("date", "LocalDate", "LocalDate"),
        ("list<int>", "List<Integer>", "List<Int>"),
        ("int[]", "int[]", "IntArray"),
        ("string[][]", "String[][]", "Array<Array<String>>"),
    ],
)
def test_a_jvm_method_spells_its_types_in_its_language(returns, java, kotlin):
    found = method("snapshot", 1, returns=returns)
    texts = (method_text(found, Language.JAVA), method_text(found, Language.KOTLIN))
    assert texts == (f"{java} snapshot()", f"snapshot(): {kotlin}")


def test_a_void_method_reads_as_java_declares_it():
    assert method_text(method("reset", 1, "timestamp: long"), Language.JAVA) == (
        "void reset(long timestamp)"
    )


def test_a_void_method_has_no_return_type_in_kotlin():
    assert method_text(method("reset", 1, "timestamp: long"), Language.KOTLIN) == (
        "reset(timestamp: Long)"
    )


@pytest.mark.parametrize(
    ("returns", "rust"),
    [
        ("double", " -> f64"),
        ("char", " -> char"),
        ("decimal", " -> Decimal"),
        ("date", " -> NaiveDate"),
        ("list<string>", " -> Vec<String>"),
        ("int[][]", " -> Vec<Vec<i32>>"),
        ("void", ""),
    ],
)
def test_a_rust_method_spells_its_types_as_the_rust_stub_does(returns, rust):
    found = method("snapshot", 1, returns=returns)
    assert method_text(found, Language.RUST) == f"snapshot(&mut self){rust}"


def test_a_method_without_parameters_has_empty_parentheses():
    assert method_text(method("size", 1, returns="int"), Language.PYTHON) == "size() -> int"


def test_a_level_adds_the_methods_declared_with_its_number():
    assert level_methods(BANK, 1) == (CREATE_ACCOUNT, DEPOSIT)


def test_methods_keep_their_declaration_order():
    assert level_methods(BANK, 2) == (TRANSFER,)


def test_a_level_beyond_the_last_adds_no_methods():
    assert level_methods(BANK, 3) == ()


# file trees


@pytest.mark.parametrize("path", ["/etc/passwd", "../outside.py", "bank/../../outside.py"])
def test_a_project_file_never_lies_outside_its_folder(path):
    with pytest.raises(ValueError, match=re.escape(f'project file "{path}"')):
        ProjectFile(path, 0, "")


def test_a_tree_knows_its_paths():
    tree = ProjectTree((ProjectFile("README.md", 3, "Hi\n"), ProjectFile("bank/bank.py", 0, "")))
    assert tree.paths == frozenset({"README.md", "bank/bank.py"})


def test_a_tree_size_is_the_size_of_its_files():
    tree = ProjectTree((ProjectFile("README.md", 3, "Hi\n"), ProjectFile("logo.png", 70, None)))
    assert tree.size == 73


def test_a_file_finds_a_file_of_its_tree_by_path():
    readme = ProjectFile("README.md", 3, "Hi\n")
    assert ProjectTree((readme,)).file("README.md") == readme


def test_a_tree_has_no_file_at_a_missing_path():
    assert ProjectTree(()).file("README.md") is None
