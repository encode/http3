import nox


@nox.session(reuse_venv=True)
def lint(session):
    source_files = ("http3/", "tests/", "setup.py", "noxfile.py")

    session.install("autoflake", "black", "flake8", "isort", "mypy")
    session.run("autoflake", "--in-place", "--recursive", *source_files)
    session.run(
        "isort",
        "--multi-line=3",
        "--trailing-comma",
        "--force-grid-wrap=0",
        "--combine-as",
        "--line-width=88",
        "--recursive",
        "--apply",
        *source_files,
    )
    session.run("black", "--line-length=88", "--target-version=py36", *source_files)
    session.run("flake8", "--max-line-length=88", "--ignore=W503,E203", *source_files)


@nox.session(reuse_venv=True)
def docs(session):
    session.install("mkdocs", "mkdocs-material")

    session.run("mkdocs", "build")


@nox.session(python=["3.6", "3.7", "3.8", "pypy3"])
def test(session):
    session.install("-r", "test-requirements.txt")
    session.install(".")

    session.run(
        "pytest", "--ignore=venv", "--cov=tests", "--cov=http3", "--cov-report="
    )
    session.run("coverage", "report", "--show-missing", "--fail-under=100")
