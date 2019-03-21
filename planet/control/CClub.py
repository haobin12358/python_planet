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
from planet.extensions.validates.club import UserWordsCreateForm

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
