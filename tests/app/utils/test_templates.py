from emergency_alerts_utils.template import Template

from app.utils.templates import get_template


def test_get_template_returns_template():
    template = get_template({"template_type": "broadcast", "content": "some content"})
    assert isinstance(template, Template)
