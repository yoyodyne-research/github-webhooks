import shotgrid


def test_context():
    ticket_id = 8558
    # sg = ShotgunHandler.get_conn()
    # ticket = sg.find_one("Ticket", [["id", "is", ticket_id]], ["sg_code_review","sg_code_review_url"])
    # print(ticket)
    sg_user = shotgrid.get_sg_user("rhaleblian")
    shotgrid.add_ticket_reply(ticket_id, "yeah.", sg_user)
