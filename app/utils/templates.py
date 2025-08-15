from emergency_alerts_utils.template import BroadcastPreviewTemplate


def get_template(reference=None, content=None):
    return BroadcastPreviewTemplate({"template_type": "broadcast", "reference": reference, "content": content})
