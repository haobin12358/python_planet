# -*- coding: utf-8 -*-
import json
import re
import uuid
from datetime import datetime

from flask import request, current_app
from planet.common.base_service import get_session, db
from planet.models.club import CompanyMessage, UserWords
from planet.common.success_response import Success
from planet.common.params_validates import parameter_required
from planet.extensions.validates.club import UserWordsCreateForm, CompanyMessageForm

class CClub():

    @get_session
    def create_userwords(self):
        """
        增加留言
        :return:
        """
        form = UserWordsCreateForm().valid_data()
        new_userwords = UserWords.create({
            "UWid": str(uuid.uuid1()),
            "UWmessage": form.UWmessage.data,
            "UWname": form.UWname.data,
            "UWtelphone": form.UWtelphone.data,
            "UWemail": form.UWemail.data
        })
        db.session.add(new_userwords)
        return Success("留言成功")

    @get_session
    def create_companymessage(self):
        """
        发布公司公告
        :return:
        """
        form = CompanyMessageForm().valid_data()
        if form.CMindex.data and int(form.CMindex.data) == 1:
            CMindex = 1
        else:
            CMindex = 2
        new_companymessage = CompanyMessage.create({
            "CMid": str(uuid.uuid1()),
            "CMtitle": form.CMtitle.data,
            "CMmessage": form.CMmessage.data,
            "CMindex": CMindex
        })
        db.session.add(new_companymessage)
        return Success("发布成功")

    @get_session
    def companymessage_list(self):
        """
        公司公告列表
        :return:
        """
        data = parameter_required()
        message_query = CompanyMessage.query.filter(
            CompanyMessage.isdelete != 1
        )
        CMindex = data.get("CMindex")
        if CMindex:
            message_query = message_query.filter(
                CompanyMessage.CMindex == CMindex
            )
        message_query = message_query.order_by(CompanyMessage.createtime.desc()).all_with_page()

        for message in message_query:
            message.add('createtime')


        return Success(data=message_query)

    @get_session
    def companymessage_message(self):
        """
        公司公告详情
        :return:
        """
        data = parameter_required(("CMid",))
        CMid = data.get("CMid")
        message_query = CompanyMessage.query.filter(
            CompanyMessage.isdelete != 1
        )
        message_query = message_query.filter(
            CompanyMessage.CMid == CMid
        )
        message_query = message_query.first()
        message_query.add("createtime")
        print(str(message_query))
        print(type(message_query))
        message_query.fill("before", None)
        message_query.fill("after", None)
        print(str(message_query))
        print(type(message_query))
        message_list = CompanyMessage.query.filter(
            CompanyMessage.isdelete != 1
        )
        message_list = message_list.order_by(CompanyMessage.createtime.desc()).all()
        index = 0
        for message in message_list:
            if CMid == message["CMid"]:
                index = message_list.index(message)
                break
        if len(message_list) == 1:
            message_query.before = {}
            message_query.after = {}
        else:
            if index == 0:
                message_query.before = {}
                message_query.after = {
                    "CMid": message_list[index + 1]["CMid"],
                    "CMtitle": message_list[index + 1]["CMtitle"]
                }
            elif index == len(message_list) - 1:
                message_query.before = {
                    "CMid": message_list[index - 1]["CMid"],
                    "CMtitle": message_list[index - 1]["CMtitle"]
                }
                message_query.after = {}
            else:
                message_query.before = {
                    "CMid": message_list[index - 1]["CMid"],
                    "CMtitle": message_list[index - 1]["CMtitle"]
                }
                message_query.after = {
                    "CMid": message_list[index + 1]["CMid"],
                    "CMtitle": message_list[index + 1]["CMtitle"]
                }

        return Success(data=message_query)

    @get_session
    def update_companymessage(self):

        return Success("更新公告成功")
