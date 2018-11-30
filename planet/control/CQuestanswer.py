import uuid

from flask import request

from planet.config.enums import AdminStatus
from planet.common.error_response import AuthorityError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_admin
from planet.models import Quest, QuestOutline, Answer, User, AnswerUser, Admin
from planet.common.request_handler import gennerc_log
from planet.common.base_service import get_session, db


class CQuestanswer():
    AnswerFields = ['QAcontent', 'QUid', 'QAid']
    QuestFields = ['QUid', 'QOid', 'QUquest']
    QuestOutlineFields = ['QOid', 'QOicon', 'QOname']

    def get_all(self):
        qo_list = QuestOutline.query.filter_(QuestOutline.isdelete == False).all()
        for qo in qo_list:
            qo.fields = self.QuestOutlineFields[:]
            question = Quest.query.filter_(Quest.isdelete == False, Quest.QOid == qo.QOid).all()
            question.fields = self.QuestFields[:]
            qo.fill('question', question)
        return Success('获取客服问题列表成功', data=qo_list)

    @get_session
    @token_required
    def get_answer(self):
        user = User.query.filter_(User.USid == request.user.id).first_('用户不存在')
        data = parameter_required(('quid'))
        answer_model = Answer.query.filter_(Answer.QUid == data.get('quid'), Answer.isdelete == False).first()
        answer_model.fields = self.AnswerFields[:]
        an_instance = AnswerUser.create({
            'QAUid': str(uuid.uuid1()),
            'QAid': answer_model.QAid,
            'USid': user.USid
        })
        db.session.add(an_instance)
        return Success('获取回答成功', data=answer_model)

    @get_session
    @token_required
    def add_questoutline(self):
        if not is_admin():
            raise AuthorityError('权限不足')

        admin = Admin.query.filter(
            Admin.ADid == request.user.id, Admin.ADstatus == AdminStatus.normal.value).first_('权限被收回')
