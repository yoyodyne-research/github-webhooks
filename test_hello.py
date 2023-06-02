import os
import shotgun_api3

CR_SUBMITTED_REPLY_TEMPLATE = \
"""
Code Review {status} by: | {reviewer}
-: | -
Review: | {url}
Action: | {reviewer} flagged the code review as _{status}_

{body}
"""

sg = shotgun_api3.Shotgun(
    os.environ.get("BASE_URL"),
    os.environ.get("SCRIPT_NAME"),
    os.environ.get("API_KEY")
)


def submit_code_review(ticket_id, sg_user, status, review_body, url):
    """
    Add Reply to SG Ticket with details of the code review submission.

    :param int ticket_num: SG Internal Ticket number.
    :param dict sg_user: SG HumanUser entity dictionary who submitted the review..
    :param str status: Status of the review (approved, rejected, etc.)
    :param str review_body: Comment the reviewer posted when submitting the review.
    :param str url: URL of the code review.
    """
    # Add Reply to Ticket with the Review comment.
    sg_user_name = sg_user.get("name", "Unknown")
    reply_text = CR_SUBMITTED_REPLY_TEMPLATE.format(
                    status=status.upper(),
                    reviewer=sg_user_name,
                    url=url,
                    body=review_body
    )
    add_ticket_reply(ticket_id, reply_text, sg_user)


def add_ticket_reply(ticket_id, reply_content, sg_user):
    """
    Add a Reply to the given Shotgun Ticket number.

    :param int ticket_id: SG Internal Ticket number.
    :param str reply_content: Reply message as a str.
    :param dict sg_user: SG HumanUser entity dict to post reply as or None.
    """
    payload = {
        "entity": {"type": "Ticket", "id": ticket_id},
        "content": reply_content
    }
    # If we have a user then we can post the Reply as that user, otherwise it will be posted
    # by the script user configured for this app.
    if sg_user:
        payload["user"] = sg_user

    result = sg.create("Reply", payload)


def get_sg_user(github_user):
    """
    Convenience function to try various ways to get the correct SG HumanUser entity
    from a Github user object (which can vary in structure)

    :param dict github_user: Github user dict.
    :returns: Shotgun HumanUser entity dict or None.
    """
    if not github_user:
        return
    user = get_user_by_email(github_user.get("email"))
    if not user:
        user = get_user_from_gh_login(github_user.get("username"))
    if not user:
        user = get_user_from_gh_login(github_user.get("name"))

    return user


def test_context():
    ticket_id = 8558
    # sg = ShotgunHandler.get_conn()
    # ticket = sg.find_one("Ticket", [["id", "is", ticket_id]], ["sg_code_review","sg_code_review_url"])
    # print(ticket)
    sg_user = get_sg_user("rhaleblian")
    add_ticket_reply(ticket_id, "yeah.", sg_user)
