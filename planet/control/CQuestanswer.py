import uuid

from flask import request

from planet.config.enums import AdminStatus, QuestAnswerNoteType, AdminAction
from planet.common.error_response import AuthorityError, ParamsError, SystemError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_admin, is_supplizer
from planet.control.BaseControl import BASEADMIN
from planet.models import Quest, QuestOutline, Answer, User, AnswerUser, Admin, QuestAnswerNote, Supplizer
from planet.common.request_handler import gennerc_log
from planet.common.base_service import get_session, db


class CQuestanswer():
    AnswerFields = ['QAcontent', 'QUid', 'QAid']
    QuestFields = ['QUid', 'QOid', 'QUquest', 'QUstatus']
    QuestOutlineFields = ['QOid', 'QOicon', 'QOname', 'QOstatus']

    def get_all_quest(self):
        """用户客服页获取所有的问题列表之后通过问题id获取答案"""
        data = request.args.to_dict()
        qotype = data.get('qotype')
        if not qotype or int(qotype) != 222:
            qotype = 111

        qo_list = QuestOutline.query.filter(
            QuestOutline.isdelete == False, QuestOutline.QOtype == int(qotype)).all()

        qo_return_list = []
        for qo in qo_list:
            qo.fields = self.QuestOutlineFields[:]
            question_list = Quest.query.filter_(Quest.isdelete == False, Quest.QOid == qo.QOid).all()
            if not question_list:
                continue
            for question in question_list:
                question.fields = self.QuestFields[:]
            qo.fill('question', question_list)
            qo_return_list.append(qo)
        return Success('获取客服问题列表成功', data=qo_return_list)

    @get_session
    @token_required
    def get_answer(self):
        """通过问题id 获取答案"""
        if is_supplizer():
            user = Supplizer.query.filter(Supplizer.SUid == request.user.id).first()
        else:
            user = User.query.filter_(User.USid == request.user.id).first_('用户不存在')
        data = parameter_required(('quid',))
        answer_model = Answer.query.filter_(Answer.QUid == data.get('quid'), Answer.isdelete == False).first_('问题不存在')
        answer_model.fields = self.AnswerFields[:]
        qu_model = Quest.query.filter_(Quest.QUid == data.get('quid'), Quest.isdelete == False).first()
        if not qu_model:
            gennerc_log('可以获取到答案， 但是获取不到问题，id为{0}'.format(data.get('quid')))
            raise SystemError('数据异常')
        answer_model.fill('ququest', qu_model.QUquest)
        an_instance = AnswerUser.create({
            'QAUid': str(uuid.uuid1()),
            'QAid': answer_model.QAid,
            'USid': user.USid
        })
        db.session.add(an_instance)
        qo = QuestOutline.query.filter_by(QOid=qu_model.QOid, isdelete=False).first_('数据异常')
        other_qu = Quest.query.filter(Quest.QOid == qo.QOid, Quest.QUid != qu_model.QUid, Quest.isdelete == False).all()
        qo.fill('other', [{'quid': qu.QUid, 'ququest': qu.QUquest} for qu in other_qu])
        answer_model.fill('qo', qo)
        return Success('获取回答成功', data=answer_model)

    @get_session
    @token_required
    def add_questoutline(self):
        """插入或更新问题分类"""
        if not is_admin():
            raise AuthorityError('权限不足')
        data = parameter_required(('qoicon', 'qoname'))
        qotype = data.get('qotype')
        admin = Admin.query.filter(
            Admin.ADid == request.user.id, Admin.ADstatus == AdminStatus.normal.value).first_('权限被收回')
        if qotype != 222:
            qotype = 111
        qo_filter = QuestOutline.query.filter_(
            QuestOutline.QOname == data.get('qoname'), QuestOutline.QOtype == qotype,
            QuestOutline.isdelete == False).first()
        # 查看是否为修改
        if data.get('qoid'):
            qo_model = QuestOutline.query.filter_(
                QuestOutline.isdelete == False, QuestOutline.QOid == data.get('qoid')).first()
            if qo_model:
                self.__update_questoutline(data, qo_model, qotype, qo_filter)
                qo_model.fields = self.QuestOutlineFields[:]
                return Success('修改问题分类成功', data=qo_model)

        # 名称重复的增加 暂时变更为修改，后期可以扩展为整个分类的迁移
        if qo_filter:
            self.__update_questoutline(data, qo_filter, qotype)
            qo_filter.fields = self.QuestOutlineFields[:]
            return Success('修改问题分类成功', data=qo_filter)

        # 正常添加
        qo_instance = QuestOutline.create({
            'QOid': str(uuid.uuid1()),
            'QOicon': data.get('qoicon'),
            'QOname': data.get('qoname'),
            'QOtype': qotype,
            'QOcreateId': admin.ADid
        })
        db.session.add(qo_instance)
        BASEADMIN().create_action(AdminAction.insert.value, 'QuestOutline', str(uuid.uuid1()))
        qo_instance.fields = self.QuestOutlineFields[:]
        return Success('创建问题分类成功', data=qo_instance)

    @get_session
    @token_required
    def add_questanswer(self):
        """插入或更新问题及答案"""
        if not is_admin():
            raise AuthorityError('权限不足')
        data = parameter_required(('qoid', 'quest', 'answer'))
        admin = Admin.query.filter(
            Admin.ADid == request.user.id, Admin.ADstatus == AdminStatus.normal.value).first_('权限被收回')
        quest_filter = Quest.query.filter_(
            Quest.QOid == data.get('qoid'), Quest.QUquest == data.get('quest'), Quest.isdelete == False).first()
        # answer_model = Answer.query.filter_(Answer.QAcontent == data.get('answer'), Answer.isdelete == False).first()
        if data.get('quid'):
            quest_model = Quest.query.filter_(Quest.QUid == data.get('quid'), Quest.isdelete == False).first()
            # 根据id 更新问题，如果问题重复则抛出异常
            self.__update_quest(data, quest_model, quest_filter)
            self.__update_answer(data.get('answer'), quest_model)
            return Success('修改问题成功')
        # 如果传入的问题已经存在但是没有传入id ，还是执行update 操作
        if quest_filter:
            self.__update_quest(data, quest_filter)

            self.__update_answer(data.get('answer'), quest_filter)

            return Success('修改问题成功')
        # 不在数据库内的问题插入
        quest_instance = Quest.create({
            'QOid': data.get('qoid'),
            'QUid': str(uuid.uuid1()),
            'QUquest': data.get('quest'),
            'QUcreateId': admin.ADid
        })
        answer_instance = Answer.create({
            'QAid': str(uuid.uuid1()),
            'QUid': quest_instance.QUid,
            'QAcontent': data.get('answer'),
            'QAcreateId': admin.ADid
        })

        db.session.add(quest_instance, BASEADMIN().create_action(AdminAction.insert.value, 'Quest', str(uuid.uuid1())))
        db.session.add(answer_instance)
        BASEADMIN().create_action(AdminAction.insert.value, 'Answer', str(uuid.uuid1()))
        return Success('创建问题成功')

    @get_session
    @token_required
    def get_all(self):
        """后台管理员查看所有的问题及答案"""
        if not is_admin():
            raise AuthorityError('权限不足')

        qo_list = QuestOutline.query.filter_(
            QuestOutline.isdelete == False).order_by(QuestOutline.createtime.desc()).all()
        for qo in qo_list:
            qo.fields = self.QuestOutlineFields[:]
            question_list = Quest.query.filter_(
                Quest.isdelete == False, Quest.QOid == qo.QOid).order_by(Quest.createtime.desc()).all()
            for question in question_list:
                question.fields = self.QuestFields[:]
                answer = Answer.query.filter_(Answer.QUid == question.QUid, Answer.isdelete == False).first_('问题答案遗失')
                answer.fields = self.AnswerFields[:]
                question.fill('answer', answer.QAcontent)
            qo.fill('question', question_list)
        return Success('获取客服问题列表成功', data=qo_list)

    def __update_questoutline(self, data, qo_model, qotype, qo_filter=None):
        """
        修改问题分类
        :param data: request的data
        :param qo_model: 通过id筛选的问题分类
        :param qo_filter: 通过名称筛选的问题分类
        :return: 出现分类名重复会报错，否则静默处理
        """
        qanaction = ""
        if data.get('qoicon') and qo_model.QOicon != data.get('qoicon'):
            qanaction += '修改icon为 {0}'.format(data.get('qoicon'))
            qo_model.QOicon = data.get('qoicon')
        if data.get('qoname') and qo_model.QOname != data.get('qoname'):

            if qo_filter:
                raise ParamsError('问题分类名不能与已有分类名相同')
            qanaction += '修改name为 {0}'.format(data.get('qoname'))
            qo_model.QOname = data.get('qoname')
        if qotype != int(qo_model.QOtype):
            qanaction += '修改类型为{0}'.format(qotype)
            qo_model.QOtype = qotype
        if qanaction:
            qan_instance = QuestAnswerNote.create({
                'QANid': str(uuid.uuid1()),
                'QANcontent': qanaction,
                'QANtargetId': qo_model.QOid,
                'QANtype': QuestAnswerNoteType.qo.value,
                'QANcreateid': request.user.id,
            })
            db.session.add(qan_instance)

    def __update_answer(self, answer, qa_model):
        """回答修改，不做对比"""
        if not answer:
            return
        answer_model = Answer.query.filter_(Answer.QUid == qa_model.QUid, Answer.isdelete == False).first()
        if not answer_model:
            db.session.add(Answer.create({
                'QAid': str(uuid.uuid1()),
                'QUid': qa_model.QUid,
                'QAcontent': answer,
                'QAcreateId': request.user.id}))
        else:
            qan_instance = QuestAnswerNote.create({
                'QANid': str(uuid.uuid1()),
                'QANcontent': '修改answer 为 {0}'.format(answer),
                'QANcreateid': request.user.id,
                'QANtargetId': answer_model.QAid,
                'QANtype': QuestAnswerNoteType.qa.value
            })
            answer_model.QAcontent = answer
            db.session.add(qan_instance)

    def __update_quest(self, data, qu_model, qu_filter=None):
        """
        修改问题分类
        :param data: request的data
        :param qu_model: 通过id筛选的问题分类
        :param qu_filter: 通过名称筛选的问题分类
        :return: 出现分类名重复会报错，否则静默处理
        """
        if data.get('quest') and qu_model.QUquest != data.get('quest'):

            if qu_filter:
                raise ParamsError('问题分类名不能与已有分类名相同')

            qu_model.QUquest = data.get('quest')

            qan_instance = QuestAnswerNote.create({
                'QANid': str(uuid.uuid1()),
                'QANcontent': '修改quest 为 {0}'.format(data.get('quest')),
                'QANcreateid': request.user.id,
                'QANtargetId': qu_model.QUid,
                'QANtype': QuestAnswerNoteType.qu.value
            })
            db.session.add(qan_instance)

    @get_session
    @token_required
    def delete_questoutline(self):
        """后台管理员删除问题分类"""
        if not is_admin():
            raise AuthorityError('权限不足')
        admin = Admin.query.filter_by_(ADid=request.user.id).first_('权限已被回收')
        data = parameter_required(('qolist',))
        qolist = data.get('qolist')
        for qoid in qolist:
            qomodel = QuestOutline.query.filter_by_(QOid=qoid).first()
            if not qomodel:
                continue
            qomodel.isdelete = True
            qulist = Quest.query.filter_by_(QOid=qoid).all()
            for qu in qulist:
                qu.isdelete = True
                qalist = Answer.query.filter_by_(QUid=qu.QUid).all()
                for qa in qalist:
                    qa.isdelete = True

            qan = QuestAnswerNote.create({
                'QANid': str(uuid.uuid1()),
                'QANcontent': '删除问题分类',
                'QANcreateid': admin.ADid,
                'QANtargetId': qoid
            })
            db.session.add(qan)
            BASEADMIN().create_action(AdminAction.delete.value, 'QuestAnswerNote', str(uuid.uuid1()))
        return Success('删除完成')

    @get_session
    @token_required
    def delete_question(self):
        """后台管理员删除问题"""
        if not is_admin():
            raise AuthorityError('权限不足')
        admin = Admin.query.filter_by_(ADid=request.user.id).first_('权限已被回收')

        data = parameter_required(('qulist',))
        qulist = data.get('qulist')
        for quid in qulist:
            qu = Quest.query.filter_by_(QUid=quid).first()
            if not qu:
                continue
            qu.isdelete = True
            qalist = Answer.query.filter_by_(QUid=qu.QUid).all()
            for qa in qalist:
                qa.isdelete = True
            qan = QuestAnswerNote.create({
                'QANid': str(uuid.uuid1()),
                'QANcontent': '删除问题',
                'QANcreateid': admin.ADid,
                'QANtargetId': quid,
                'QANtype': QuestAnswerNoteType.qu.value,
            })
            db.session.add(qan)
            BASEADMIN().create_action(AdminAction.delete.value, 'QuestAnswerNote', str(uuid.uuid1()))

        return Success('删除完成')
    #
    # @get_session
    # @token_required
    # def online_questoutline(self):
    #     if not is_admin():
    #         raise AuthorityError('权限不足')
    #     admin = Admin.query.filter_by_(ADid=request.user.id).first_('权限已被回收')
    #     data = parameter_required(('qoid',))
    #     qo = QuestOutline.query.filter_by_(QOid=data.get('qoid'))
    #  todo 问题和问题分类是否上线状态增加编辑接口
