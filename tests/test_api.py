from pathlib import Path
import os
import subprocess
import sys
import textwrap
import zipfile
import shutil
import sysconfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_index_page_loads_from_installed_package(tmp_path):
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-build-isolation",
            "--no-deps",
            "-w",
            str(wheelhouse),
            str(PROJECT_ROOT),
        ],
        check=True,
        cwd=PROJECT_ROOT,
    )

    wheel_path = next(wheelhouse.glob("*.whl"))

    with zipfile.ZipFile(wheel_path) as wheel_file:
        metadata_name = next(name for name in wheel_file.namelist() if name.endswith(".dist-info/METADATA"))
        metadata = wheel_file.read(metadata_name).decode()

    assert "Requires-Dist: Flask>=3.0" in metadata
    assert "Requires-Dist: openpyxl>=3.1" in metadata
    assert "Requires-Dist: rapidocr-onnxruntime>=1.4" in metadata

    venv_dir = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True, cwd=PROJECT_ROOT)

    venv_python = venv_dir / ("Scripts" if os.name == "nt" else "bin") / (
        "python.exe" if os.name == "nt" else "python"
    )

    venv_site_packages = Path(
        subprocess.check_output(
            [
                str(venv_python),
                "-c",
                "import sysconfig; print(sysconfig.get_paths()['purelib'])",
            ],
            text=True,
        ).strip()
    )
    current_site_packages = Path(sysconfig.get_paths()["purelib"])

    for package_name in [
        "flask",
        "blinker",
        "click",
        "itsdangerous",
        "jinja2",
        "markupsafe",
        "werkzeug",
    ]:
        shutil.copytree(current_site_packages / package_name, venv_site_packages / package_name)
        for dist_info in current_site_packages.glob(f"{package_name}*.dist-info"):
            shutil.copytree(dist_info, venv_site_packages / dist_info.name)

    subprocess.run([str(venv_python), "-m", "pip", "install", "--no-deps", str(wheel_path)], check=True, cwd=PROJECT_ROOT)

    script = textwrap.dedent(
        """
        from pathlib import Path
        import sysconfig

        from expense_record import __file__ as package_file
        from expense_record.app import create_app

        package_path = Path(package_file).resolve()
        install_dir = Path(sysconfig.get_paths()["purelib"]).resolve()
        assert package_path.is_relative_to(install_dir)
        assert (install_dir / "expense_record" / "templates" / "index.html").exists()
        assert (install_dir / "expense_record" / "static" / "app.css").exists()
        assert (install_dir / "expense_record" / "static" / "app.js").exists()

        app = create_app({"TESTING": True})
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        assert b"Expense Screenshot Tool" in response.data
        assert client.get("/static/app.css").status_code == 200
        assert client.get("/static/app.js").status_code == 200
        """
    )

    subprocess.run([str(venv_python), "-c", script], check=True, cwd=PROJECT_ROOT)
