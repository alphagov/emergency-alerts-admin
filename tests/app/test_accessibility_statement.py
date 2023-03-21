import re
import subprocess
from datetime import datetime

import pytest


def test_last_review_date():
    statement_file_path = "app/templates/views/accessibility_statement.html"

    # test local changes against main for a full diff of what will be merged
    statement_diff = subprocess.run(
        [f"git diff --exit-code origin/main -- {statement_file_path}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )

    # if statement has changed, test the review date was part of those changes
    if statement_diff.returncode == 1:

        if "Could not access 'origin/main'" in statement_diff.stderr.decode("utf-8"):
            pytest.skip(
                "The build context inside container is not cloned from github, so "
                "this test will fail. Ensure this test is run locally to verify "
                "the correctness of the 'Last updated' date string."
            )

        raw_diff = statement_diff.stdout.decode("utf-8")
        today = datetime.now().strftime("%d %B %Y")
        with open(statement_file_path, "r") as statement_file:
            current_review_date = re.search(
                (r'"Last updated": "(\d{1,2} [A-Z]{1}[a-z]+ \d{4})"'), statement_file.read()
            ).group(1)

        # guard against changes that don't need to update the review date
        if current_review_date != today:
            assert '"Last updated": "' in raw_diff
