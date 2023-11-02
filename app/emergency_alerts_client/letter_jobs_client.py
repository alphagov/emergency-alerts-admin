from app.emergency_alerts_client import EmergencyAlertsAdminAPIClient


class LetterJobsClient(EmergencyAlertsAdminAPIClient):
    def submit_returned_letters(self, references):
        return self.post(url="/letters/returned", data={"references": references})


letter_jobs_client = LetterJobsClient()
