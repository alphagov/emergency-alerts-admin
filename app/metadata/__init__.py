from flask import Blueprint

metadata = Blueprint("metadata", __name__)

from app.metadata.views import robots  # noqa isort:skip
