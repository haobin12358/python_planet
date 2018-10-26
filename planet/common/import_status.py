# *- coding:utf8 *-


def import_status(msg_key, sta_key, code_key=None):
    from config import messages, status, status_code
    if code_key:
        msg, sta, code = eval("messages.{0}, status.{1}, status_code.{2}".format(msg_key, sta_key, code_key))
        return {"message": msg, "status": sta, "status_code": code}
    else:
        msg, sta = eval("messages.{0}, status.{1}".format(msg_key, sta_key))
        return {"message": msg, "status": sta}
