import io
import shutil
from importlib import metadata
from pathlib import Path
import os
import subprocess
import sys
import textwrap
import zipfile
import sysconfig

from expense_record.app import create_app
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _distribution_index(site_packages: Path) -> dict[str, metadata.Distribution]:
    return {
        canonicalize_name(dist.metadata["Name"]): dist
        for dist in metadata.distributions(path=[str(site_packages)])
        if dist.metadata.get("Name")
    }


def _dependency_closure(root_names: list[str], site_packages: Path) -> list[metadata.Distribution]:
    distributions = _distribution_index(site_packages)
    required: dict[str, metadata.Distribution] = {}
    pending = [canonicalize_name(name) for name in root_names]

    while pending:
        name = pending.pop()
        if name in required:
            continue
        dist = distributions[name]
        required[name] = dist
        for requirement_text in dist.requires or []:
            requirement = Requirement(requirement_text)
            if requirement.marker and not requirement.marker.evaluate():
                continue
            pending.append(canonicalize_name(requirement.name))

    return list(required.values())


def _copy_distribution(dist: metadata.Distribution, destination: Path) -> None:
    for file in dist.files or []:
        source = dist.locate_file(file)
        target = destination / file
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)


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
        assert any(name.endswith("static/nested/fixture.txt") for name in wheel_file.namelist())

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

    for distribution in _dependency_closure(["Flask"], current_site_packages):
        _copy_distribution(distribution, venv_site_packages)

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
        assert (install_dir / "expense_record" / "static" / "nested" / "fixture.txt").exists()

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


def test_extract_endpoint_parses_uploaded_image(tmp_path, monkeypatch):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    monkeypatch.setattr(
        "expense_record.api.run_ocr_lines",
        lambda image_bytes: ["微信支付", "2026-03-30 18:21", "瑞幸咖啡", "￥23.50"],
    )

    response = client.post(
        "/api/extract",
        data={"image": (io.BytesIO(b"fake image bytes"), "receipt.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "row": {"date": "2026-03-30", "merchant_item": "瑞幸咖啡", "amount": "23.50"},
        "lines": ["微信支付", "2026-03-30 18:21", "瑞幸咖啡", "￥23.50"],
    }


def test_save_endpoint_persists_row(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    response = client.post(
        "/api/save",
        json={"date": "2026-03-30", "merchant_item": "瑞幸咖啡", "amount": "23.50"},
    )

    assert response.status_code == 200
    assert response.get_json()["rows"] == [
        {"date": "2026-03-30", "merchant_item": "瑞幸咖啡", "amount": "23.50"}
    ]


def test_rows_endpoint_lists_saved_rows(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    client.post(
        "/api/save",
        json={"date": "2026-03-30", "merchant_item": "瑞幸咖啡", "amount": "23.50"},
    )

    response = client.get("/api/rows")

    assert response.status_code == 200
    assert response.get_json()["rows"] == [
        {"date": "2026-03-30", "merchant_item": "瑞幸咖啡", "amount": "23.50"}
    ]
