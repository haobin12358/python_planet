from flask import request
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.models import Quest, QuestOutline, Answer, User, AnswerUser
from planet.common.request_handler import gennerc_log
from planet.extensions.register_ext import db

class CQuestanswer():
    def get_all(self):
        qo_list = QuestOutline.query.filter_(QuestOutline.isdelete == False).all()
        for qo in qo_list:
            question = Quest.query.filter_(Quest.isdelete == False, Quest.QOid == qo.QOid).all()
            qo.fill('question', question)
        return Success('获取客服问题列表成功', data=qo_list)

    @token_required
    def get_answer(self):
        user = User.query.filter_(User.USid == request.user.id).first_('用户不存在')

        data = parameter_required(('quid'))
        answer_model = Answer.query.filter_(Answer.QUid == data.get('quid'), Answer.isdelete == False).first()
        AnswerUser.create({
            ''
        })
        return Success('获取回答成功', data=answer_model)
