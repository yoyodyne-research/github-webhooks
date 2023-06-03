import logging
import os
import re
import shotgun_api3

from . import constants

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

sg = shotgun_api3.Shotgun(
    os.environ.get("BASE_URL"),
    os.environ.get("SCRIPT_NAME"),
    os.environ.get("API_KEY")
)


def assign_code_review(ticket_num, to_sg_user, pr_title, pr_body, pr_url, by_sg_user):
    """
    Update SG ticket with the assigned code reviewer and set status to Pending Code Review. Add a
    Reply to the Ticket with the details.

    :param int ticket_num: SG internal ticket number.
    :param dict to_sg_user: SG user entity dictionary (with 'name' key as well).
    :param str pr_title: Title of the pull request.
    :param str pr_body: Body of the pull request.
    :param str pr_url: HTML url on Github for the pull request.
    :param dict by_sg_user: SG user entity dictionary (with 'name' key as well).
    """
    # Update the SG Ticket fields assigning the code reviewer and setting status to Pending CR
    payload = {
        "sg_status_list": "code",
        "sg_code_review": to_sg_user,
        "sg_code_review_url": {"url": pr_url, "name": "Github Pull Request"}
    }
    result = sg.update("Ticket", ticket_num, payload)

    logger.debug("Updated SG Ticket %d: %s" % (ticket_num, result))
    # Add comment with the PR comment
    sg_user_name = to_sg_user.get("name", "Unknown")
    reply_text = constants.CR_ASSIGNED_REPLY_TEMPLATE.format(
                    assignee=sg_user_name,
                    url=pr_url,
                    title=pr_title,
                    body=pr_body
    )
    add_ticket_reply(ticket_num, reply_text, by_sg_user)


def unassign_code_review(ticket_num):
    """
    Update SG Ticket and remove code review assignment.

    :param int ticket_num: SG Internal Ticket number.
    """
    payload = {
        "sg_code_review": None
    }
    result = sg.update("Ticket", ticket_num, payload)
    logger.debug("Updated SG Ticket %d: %s" % (ticket_num, result))


def notify_pull_request_updated(ticket_num, pr_url, changed, pr_title, pr_body, sg_user):
    """
    Add Reply to Shotgun Ticket with the new title and description of the pull request.

    :param int ticket_num: SG Internal Ticket number.
    :param str pr_url: Pull request url on Github.
    :param list changed: List of changed fields in the pull request (eg. ["title"]
    :param str pr_title: Title of the pull request.
    :param str pr_body: Body of the pull request.
    :param dict sg_user: SG HumanUser entity dict or None.
    """
    # Check if the Ticket has CR Assigned. If not, we don't really need to update the ticket.
    # The Github web hook in this workflow doesn't contain information about the Reviewers so
    # we need to query Shotgun for this.
    sg_ticket = sg.find_one("Ticket", [["id", "is", ticket_num]], ["sg_code_review"])
    if not sg_ticket:
        logger.info(
                "Unable to find Ticket #%d in Shotgun to post edited PR" % ticket_num
        )
        return

    # Note: This could miss an edge case where the reviewer is assigned in GH but not in SG.
    if not sg_ticket["sg_code_review"]:
        # logger.warning(
        #         "Code Review is not assigned for Ticket #%d, not posting edited Pull Request "
        #         "description" % ticket_num
        # )
        # return
        assignee = None
    else:
        assignee = sg_ticket["sg_code_review"]["name"]

    # Add comment with the PR comment
    reply_text = constants.CR_EDITED_REPLY_TEMPLATE.format(
                     assignee=assignee,
                     url=pr_url,
                     field=" and ".join(changed),
                     title=pr_title,
                     body=pr_body
    )
    add_ticket_reply(ticket_num, reply_text, sg_user)


def submit_code_review(ticket_num, sg_user, status, review_body, url):
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
    reply_text = constants.CR_SUBMITTED_REPLY_TEMPLATE.format(
                    status=status.upper(),
                    reviewer=sg_user_name,
                    url=url,
                    body=review_body
    )
    add_ticket_reply(ticket_num, reply_text, sg_user)


def add_ticket_reply(ticket_num, reply_content, sg_user):
    """
    Add a Reply to the given Shotgun Ticket number.

    :param int ticket_num: SG Internal Ticket number.
    :param str reply_content: Reply message as a str.
    :param dict sg_user: SG HumanUser entity dict to post reply as or None.
    """
    payload = {
        "entity": {"type": "Ticket", "id": ticket_num},
        "content": reply_content
    }
    # If we have a user then we can post the Reply as that user, otherwise it will be posted
    # by the script user configured for this app.
    if sg_user:
        payload["user"] = sg_user

    result = sg.create("Reply", payload)
    logger.debug("Added Reply to SG Ticket %d: %s" % (ticket_num, result))


def get_component(name):
    """ 
    Find Component given a name and project.

    :param str name: Component name
    :returns dict: Shotgun component entity dict or None.
    """
    return sg.find_one(
            constants.APP_SETTINGS["COMPONENT_ENTITY_TYPE"],
            [["code", "is", name]]
    )


def parse_ticket_from_str(title_str):
    """
    Get SG Internal ticket number out of the pull request title.

    Looks for the first #12345 in the string, if nothing is found, falls back on finding a number
    at the beginning of the string like "12345 some bugfix" which is the default behavior
    when creating a pull request from a branch named 12345_some_bugfix.

    Since our convention is to create topic branches starting with a ticket number this should
    succeed by default as well as if someone renames the Pull Request to be more specific,
    "For #12345 fixing some bug". In the case where there are multiple ticket numbers in the
    string only the first one will be matched.

    Examples:
        - "For #12345 some bug fix" returns 12345.
        - "For #12345 fix 500 errors" returns 12345.
        - "For #12345, #67890 some bug fix" returns 12345 since it's the first.
        - "12345 some bug fix" returns 12345.
        - "12345 fix 500 errors" returns 12345.
        - "66666 some bug fix for #12345" returns 12345 since # notation takes precedence over the
            title starting with a number.
        - "12345_some_branch_name" returns 12345

    :param str title_str: Title of the pull request
    :returns: Ticket number on SG Internal as int.
    """
    # Try to find the first number starting with a # "For #12345 some bug fix".
    # result = re.search("#(\d+)\D", title_str)
    logger.debug("Parsing for Ticket from: %s" % title_str)
    result = re.search(r"\s*#(\d+)\b", title_str)
    if not result:
        # No match. Find the number at the beginning of the string. "12345 some bug fix"
        result = re.match(r"^(\d+)(\b)?.*", title_str)
        if not result:
            # No match. Find the number from a dedicated ticket branch "Ticket/12345 some bug fix"
            result = re.match(r"^ticket\/(\d+)\s", title_str, re.IGNORECASE)
            if not result:
                logger.debug("No Ticket found.")
                return

    ticket_id = int(result.group(1))
    logger.debug("Ticket found: %d" % ticket_id)
    return ticket_id


def get_project_from_repo(repo_name):
    """
    Return SG Project associated with repo_name.

    Currently all repos are tracked in the same THR3D_DEV project but this
    allows for future flexibility.

    :param str repo_name: Github repo name.
    :returns dict: Shotgun Project entity dict.
    """
    return constants.APP_SETTINGS["THR3D_DEV_PROJECT_ENTITY"]


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


def create_revision(project, repo, branch, revision, url, author, message):
    """
    Create a Shotgun Revision

    :param dict project: Shotgun Project entity dict.
    :param str repo: Github repo name.
    :param str branch: Branch name
    :param str revision: Revision name
    :param str url: Commit url on Github.
    :param dict author: Github author dict from commit dict.
    :param str message: Commit message.
    """
    sg_branch = "%s/%s" % (repo, branch)
    # Special format for Shotgun web app.
    if repo == "shotgun":
        sg_branch = branch

    # If the Ticket number isn't in the commit message, try and get it from the
    # branch name assuming it starts with a number (eg. 12345_some_branch_name).
    # If we find it in the branch name, we prepend the commit message with it
    # so Shotgun's automatic Ticket parsing will pick it up.
    ticket_id = parse_ticket_from_str(message)
    if not ticket_id:
        ticket_id = parse_ticket_from_str(branch)
        if ticket_id:
            message = "for #%d: %s" % (ticket_id, message)

    revision_data = {
        "project": project,
        "code": revision,
        "description": message,
        "attachment": {"name": "Github", "url": url},
        "sg_branch": sg_branch,
        "sg_component": get_component(repo)
    }

    user = get_sg_user(author)
    if user:
        revision_data["created_by"] = user

    logger.info("Creating Revision: %s" % revision_data)
    sg_revision = sg.create("Revision", revision_data)
    logger.info("Created Revision: %s" % sg_revision)


def find_latest_release(sg_component):
    """
    Return the latest Release for the given componenet from Shotgun.

    :param dict sg_component: SG Component entity dict.
    :return: SG Release entity dict or None.
    """
    filters = [
        ["sg_component", "is", sg_component],
        ["sg_status_list", "is_not", "omt"]
    ]
    # Find the latest Release by release date and fall back on descending id.
    sg_release = sg.find_one("Release", filters, ["code", "sg_release_url"],
                              order=[
                                  {"field_name": "sg_release_date", "direction": "desc"},
                                  {"field_name": "id", "direction": "desc"}
                              ])

    return sg_release


def create_release(project, component_name, version_num, created_by, release_date, url):
    """
    Create a Shotgun Release

    This creates the basic info for a Release in Shotgun.

    Todo: In the future it would be nice to include the release notes, and
          stability of the release. This would require using the Github
          API to query for more information.

    :param dict project: Shotgun Project entity dict.
    :param str component_name: Component name in Shotgun to link to.
    :param str version_num: Version of the release
    :param dict created_by: Github author dict from commit dict.
    :param object release_date: datetime.date object representing the release date.
    :param str url: Github url for the tag or release.
    """
    sg_component = get_component(component_name)
    release_data = {
        "project": project,
        "sg_component":  sg_component,
        "code": version_num,
        "sg_release_date": str(release_date),  # SG dates are str
        "sg_release_url": {"url": url, "name": "Compare in Github"}
    }

    # Create Github url that shows the diff between this release and the last one.
    logger.info("sg_component: %s" % sg_component)
    latest_release = find_latest_release(sg_component)
    logger.info("latest_release: %s" % latest_release)
    if latest_release:
        # https://github.com/thr3dcgi/thr3dhooks/compare/v0.0.2...v0.0.3
        url_link = latest_release.get("sg_release_url", "")
        if url_link:
            url = url_link["url"].rsplit("/", 1)[0]
            release_data["sg_release_url"] = {
                "url": "%s/%s...%s" % (url, latest_release["code"], version_num),
                "name": "Compare in Github"
            }

    user = get_sg_user(created_by)
    if user:
        release_data["created_by"] = user

    sg_release = sg.create("Release", release_data)
    logger.info("Created Release: %s" % sg_release)


def mark_release_deleted(component_name, version_num):
    """
    Update status on the Release with given component and version number to signify it's been
    deleted.

    :param str component_name: Name of the Component Release is linked to.
    :param str version_num: Version number of the Release
    """
    filters = [
        ["code", "is", version_num],
        ["sg_component.%s.code" % constants.APP_SETTINGS["COMPONENT_ENTITY_TYPE"], "is", component_name]
    ]
    sg_release = sg.find_one("Release", filters)

    if not sg_release:
        logger.warning(
            "Unable to find Release '%s %s'" % (component_name, version_num)
        )
        return
    else:
        payload = {
            "sg_status_list": "omt",
            "sg_release_url": None
        }
        sg.update("Release", sg_release["id"], payload)
        logger.info("Set Release %s as deleted." % sg_release)


def create_component(component_name, description, status):
    """
    Create a new Component in Shotgun

    :param str component_name: Name of the Component to create.
    :param str description: Description of the Component.
    :param str status: Short code of
    :return:
    """
    payload = {
        "code": component_name,
        "description": description,
        "sg_status_list": status
    }
    sg_component = sg.create(constants.APP_SETTINGS["COMPONENT_ENTITY_TYPE"], payload)
    logger.info("Created Component: %s" % sg_component)


def update_component_status(component_name, status):
    """
    Create a new Component in Shotgun

    :param str component_name: Name of the Component to create.
    :param str status: Short code of
    :return:
    """
    sg_component = get_component(component_name)
    if not sg_component:
        logger.info("No Component found in Shotgun named: %s" % component_name)
        return

    payload = {
        "sg_status_list": status
    }
    sg_component = sg.update(constants.APP_SETTINGS["COMPONENT_ENTITY_TYPE"], sg_component["id"], payload)
    logger.info("Updated Component status: %s" % sg_component)
