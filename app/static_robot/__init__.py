from flask import Blueprint

static = Blueprint("static", __name__, static_folder="static")

from app.static_robot.views import routes  # noqa isort:skip
