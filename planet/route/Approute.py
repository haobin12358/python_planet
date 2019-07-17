# from flask import request
#
# from flaskrun import app, socketio
#
#
# @app.route('/api/v2/mes')
# def mes():
#     #     return 'ok'
#     event_name = 'test'
#     data = request.args.get("msg")
#     broadcasted_data = {'data': data}
#     print("publish msg==>", broadcasted_data)
#     socketio.emit(event_name, broadcasted_data, broadcast=True)
#     return 'send msg successful!'
