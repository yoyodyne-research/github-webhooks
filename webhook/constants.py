import os

# App settings
APP_SETTINGS = dict(
    # The PullRequestEvent has multiple actions, these are the only ones we care about.
    # See https://developer.github.com/v3/activity/events/types/#pullrequestevent
    VALID_CR_ASSIGNMENT_ACTIONS=["review_requested", "review_request_removed", "edited"],
    # The PullRequestReviewEvent is always sent with the action "submitted" but has a separate
    # key "state" which indicates whether the PullRequestReviewEvent is approving or rejecting
    # the Pull Request. Or if it is just a comment on the PullRequest (which can be a general
    # comment in the thread, or specific comment on a line of code.
    # Note: The PullRequestReviewEvent was in beta at the time this was implemented and there
    # were some inconsistencies with the values sent. We know we don't want the comments so we
    # just ignore that one and assume any other state is ok. The way this works may have changed
    # since the beta.
    # See https://developer.github.com/v3/activity/events/types/#pullrequestreviewevent
    IGNORE_CR_SUBMITTED_STATES=["commented"],
    # We link Revisions to Components where possible.
    COMPONENT_ENTITY_TYPE="CustomNonProjectEntity01",
    COMPONENT_STATUSES={
        "created": "ip",
        "deleted": "omt",
        "publicized": "public",
        "privatized": "priv"
    },
    THR3D_DEV_PROJECT_ENTITY={"type": "Project", "id": 148},
    SG_SERVER_URL=os.environ.get("SG_SERVER_URL"),
    SG_SCRIPT_NAME=os.environ.get("SG_SCRIPT_NAME"),
    SG_API_KEY=os.environ.get("SG_API_KEY"),
    DEBUG=False,
)

# This is the default status response we return for the web hooks since they are one-way.
# content, status code
HTTP_RESPONSE_NO_CONTENT = "", 204

# Template for Reply when a code review is assigned.
# Requires: assignee name, pull request url, pull request title, pull request description.
# Since Github returns everything in unicode, and we need to be able to handle special chars
# in names as well we stick to unicode for all of the Reply templates for simplicity.
CR_ASSIGNED_REPLY_TEMPLATE = \
"""
### {title}
Code Review assignee: | {assignee}
-: | -
Pull Request: | {url}
Action: | {assignee} was assigned code review

{body}

---
"""

# Template for Reply when a code review is edited.
# Requires: assignee name, pull request url, changed fields str
CR_EDITED_REPLY_TEMPLATE = \
"""
### {title}
Code Review assignee: | {assignee}
-: | -
Pull Request: | {url}
Action: | The *{field}* was updated on the pull request below:

{body}

---
"""

CR_SUBMITTED_REPLY_TEMPLATE = \
"""
Code Review {status} by: | {reviewer}
-: | -
Review: | {url}
Action: | {reviewer} flagged the code review as _{status}_

{body}

---
"""
