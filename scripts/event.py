import os

import shotgrid


def pull_request():
    pr_title = os.getenv("TITLE")
    ticket_num = shotgrid.parse_ticket_from_str(pr_title)
    sg_user = shotgrid.get_user_from_gh_login("rhaleblian")
    pr_url = os.getenv("URL")
    changed = ["title", "pr_url"]
    pr_body = "whatever."
    shotgrid.notify_pull_request_updated(ticket_num, pr_url, changed, pr_title, pr_body, sg_user)

pull_request()
