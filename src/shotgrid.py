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


def get_user_by_email(email):
    """
    Find author based on email address.

    Tries to match the author account email with an Email address on Shotgun, falls
    back to searching on the Github Email field.

    :param str email: email address from github
    :returns dict: Shotgun HumanUser entity dict or None.
    """
    if not email:
        return
    user = sg.find_one("HumanUser", [["email", "is", email]])
    if not user:
        user = sg.find_one("HumanUser", [["sg_github_email", "is", email]])

    return user


def get_user_from_gh_login(github_login):
    """
    Lookup SG HumanUser entity with the specified Github login.

    :param str github_login: Github login to look up on Shotgun internal.
    :returns: SG HumanUser as a standard entity dictionary or None.
    """
    if not github_login:
        return

    return sg.find_one("HumanUser", [["sg_github_login", "is", github_login]], ["name"])
