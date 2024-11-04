from emergency_alerts_utils.template import BroadcastPreviewTemplate


def get_template(
    template,
):
    if "broadcast" == template["template_type"]:
        return BroadcastPreviewTemplate(
            template,
        )
