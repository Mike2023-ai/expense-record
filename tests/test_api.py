from pathlib import Path
import os
import subprocess
import sys
import textwrap


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_index_page_loads_from_installed_package(tmp_path):
    install_dir = tmp_path / "install"
    install_dir.mkdir()

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(install_dir),
            str(PROJECT_ROOT),
        ],
        check=True,
        cwd=PROJECT_ROOT,
    )

    script = textwrap.dedent(
        """
        from pathlib import Path

        from expense_record import __file__ as package_file
        from expense_record.app import create_app

        package_path = Path(package_file).resolve()
        install_dir = Path(r"{install_dir}").resolve()
        assert package_path.is_relative_to(install_dir)
        assert (install_dir / "expense_record" / "templates" / "index.html").exists()
        assert (install_dir / "expense_record" / "static" / "app.css").exists()
        assert (install_dir / "expense_record" / "static" / "app.js").exists()

        app = create_app({{"TESTING": True}})
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        assert b"Expense Screenshot Tool" in response.data
        assert client.get("/static/app.css").status_code == 200
        assert client.get("/static/app.js").status_code == 200
        """
    ).format(install_dir=install_dir)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(install_dir)

    subprocess.run([sys.executable, "-c", script], check=True, env=env, cwd=PROJECT_ROOT)
