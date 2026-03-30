from flask import Flask, render_template

from expense_record.api import api
from expense_record.config import Config, resolve_excel_path


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)
    if config:
        app.config.update(config)
    if not config or "EXCEL_PATH" not in config:
        app.config["EXCEL_PATH"] = resolve_excel_path()
    app.register_blueprint(api)

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    return app
