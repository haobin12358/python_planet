import time
from random import randint
from datetime import datetime
from planet import create_app
from planet.config.enums import TicketStatus, TicketsOrderStatus, TicketPayType
from planet.extensions.register_ext import db
from planet.models import User, Ticket, TicketsOrder
from sqlalchemy import false

false = false()


def add_ticket_order(tiid, usids):
    instance_list = []
    with db.auto_commit():
        for usid in usids:
            score = 5 * randint(10, 80)
            print('score: {}'.format(score))
            to = TicketsOrder.create({'TSOid': str(datetime.now().timestamp()) + str(randint(10, 10000)),
                                      'USid': usid,
                                      'TIid': tiid,
                                      'TSOstatus': TicketsOrderStatus.pending.value,
                                      'TSOtype': TicketPayType.scorepay.value,
                                      'TSOactivation': score
                                      })
            instance_list.append(to)
        db.session.add_all(instance_list)
    return len(instance_list)


def list_pending_act(x=None):
    tickets = Ticket.query.filter(Ticket.isdelete == false, Ticket.TIstatus == TicketStatus.active.value
                                  ).order_by(Ticket.TIstartTime.asc()).all()
    t_list = [{'index': index, 'name': t.TIname, 'tiid': t.TIid} for index, t in enumerate(tickets)]
    if not x and x != 0:
        print('>>>  目前所有进行中的抢票: {}个 <<< \n\n {}\n\n'.format(len(tickets), '\n'.join(map(lambda v: str(v), t_list))))
    else:
        return t_list[x].get('tiid'), '\n选择了 >>> {} <<<\n'.format(t_list[x].get('name'))


def list_mock_user(usids=None, others_usid=None):
    users = User.query.filter(User.isdelete == false, User.USid.ilike('id000%')
                              ).order_by(User.USid.asc(), User.createtime.desc()).all()
    msg = ''
    if usids:
        users = filter(lambda k: k.USid in usids, users)
        msg = '已加入的用户为:'
    elif others_usid:
        users = filter(lambda k: k.USid not in others_usid, users)
        msg = '剩余可加入的用户为:'
    else:
        print('\n>>> 目前所有虚拟用户({}个): <<< \n'.format(len(users)))
    if msg:
        users_list = [{'index': index, 'usid': u.USid, 'name': u.USname} for index, u in enumerate(users)]
        print('{} \n{}'.format(msg, '\n'.join(map(lambda k: str(k), users_list))))
        return users_list


def query_ticket_order(tiid):
    tso_qurey = TicketsOrder.query.filter(TicketsOrder.isdelete == false, TicketsOrder.TIid == tiid,
                                          TicketsOrder.TSOstatus == TicketsOrderStatus.pending.value)
    total_count = tso_qurey.count()
    print('\n  >>> 该门票共有{}条申请记录 <<< \n'.format(total_count))
    mock_tso = tso_qurey.filter(TicketsOrder.USid.ilike('id000%')).all()
    mock_users = [{'usid': to.USid,
                   'score': to.TSOactivation,
                   'name': db.session.query(User.USname).filter(User.isdelete == false, User.USid == to.USid).scalar(),
                   }
                  for to in mock_tso]
    mock_users.sort(key=lambda y: y.get('usid'))
    print('已在该门票记录中添加的虚拟用户为({}个): \n {}'.format(len(mock_users), '\n'.join(map(lambda x: str(x), mock_users))))
    usids = [i.get('usid') for i in mock_users]
    return usids


def run():
    x = input('选择活动， 输入相应活动的index值(数字): ')
    tiid = None
    while x:
        try:
            tiid, msg = list_pending_act(int(x))
            print(msg)
            x = None
        except (ValueError, IndexError):
            x = input('输入正确的index :')
    print('\n' + '-' * 20 + '\n')
    joined_usid = query_ticket_order(tiid)
    print('-' * 20 + '\n')
    can_join_list_usid = list_mock_user(others_usid=joined_usid)
    choices = input('\n输入要加入该活动的用户index值(数字)，可一次性输入多个，用英文状态逗号隔开，如 0,1,2,3 :')
    choose = choices.split(',')
    print(choose)
    usids = None
    while choose:
        try:
            usids = [can_join_list_usid[int(i)].get('usid') for i in choose]
            choose = None
        except (ValueError, IndexError):
            choose = input('\n输入正确的用户index值(数字)，可一次性输入多个，用英文状态逗号隔开，如 0,1,2,3 :')
            choose = choose.split(',')

    print(usids)
    counts = add_ticket_order(tiid, usids)
    print('-' * 20 + '\n')
    print('成功添加 {} 条记录'.format(counts))
    time.sleep(1)
    joined_usid = query_ticket_order(tiid)
    print('-' * 20 + '\n')
    list_mock_user(others_usid=joined_usid)
    input('\n >>>按回车键返回活动选择列表<<< \n')
    return


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        list_mock_user()
        print('\n' + '-' * 20 + '\n')
        while True:
            list_pending_act()
            run()
