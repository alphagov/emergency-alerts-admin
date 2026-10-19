from dataclasses import dataclass


@dataclass(frozen=True)
class BroadcastLabels:
    submit_for_approval_button: str = "Submit for approval"
    submit_for_approval_confirmation: str = (
        "This is a live service where alerts can be sent to the public. "
        "Are you sure you want to submit this alert for approval?"
    )
    submit_for_approval_confirmation_button: str = "submit for approval"


@dataclass(frozen=True)
class ServiceLabels:
    training_service_status: str = "This is a training service. You cannot send out alerts to the public from here."


@dataclass(frozen=True)
class Labels:
    broadcast: BroadcastLabels = BroadcastLabels()
    service: ServiceLabels = ServiceLabels()


LABELS = Labels()
