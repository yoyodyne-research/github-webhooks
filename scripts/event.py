import shotgrid

sg_user = shotgrid.get_sg_user("rhaleblian")
kwargs = {
    "ticket_id": "8558",
    "sg_user": sg_user,
    "status": "foo",
    "review_body": "hi!",
    "url": "http://google.com"
}
shotgrid.submit_code_review(**kwargs)
