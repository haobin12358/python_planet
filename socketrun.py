from flask import render_template, request, session
from planet import socketio, create_scoketapp
from planet.route.RouteSocket import Mynamespace

scoketapp = create_scoketapp()


@scoketapp.route('/socket/v2/test')
def hi():
    #     return 'ok'
    return render_template('index.html')


@scoketapp.route('/api/v2/mes')
def mes():
    #     return 'ok'
    event_name = 'test'
    data = request.args.get("msg")
    roomid = request.args.get('room')
    broadcasted_data = {'data': data}
    print("publish msg==>", broadcasted_data)
    # socketio.emit(event_name, broadcasted_data, broadcast=True)
    socketio.emit(event_name, broadcasted_data, room=roomid)
    return 'send msg successful!'


@socketio.on('json')
def handle_json(json):
    print(session.get('id'))
    # session['id'] = 'json'
    print('received json: ' + str(json))


@socketio.on('message')  # 接收匿名send消息
def message_handler(*args):
    print(session.get('id'))
    # session['id'] = 'message'
    print('recive {0} data from client'.format(type(args[0])), args)
    return args


if __name__ == '__main__':
    socketio.init_app(scoketapp)
    socketio.on_namespace(Mynamespace('/'))

    socketio.run(scoketapp, port=7444, debug=True)
