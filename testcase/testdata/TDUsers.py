from flask import current_app
from planet.common.base_service import get_session, db
from planet.models.user import User


class TDUsers():

    @get_session
    def test_user_data(self):
        data_text = ""
        current_app.logger.info(">>>>>>>>>>>>>>>>>>>>>>User test data start>>>>>>>>>>>>>>>>>>>>>>>>")
        all_user = User.query.filter(User.isdelete == 0).all()
        for user in all_user:
            usid = user.USid
            if not usid:
                current_app.logger.info("存在主键为空的脏数据")
                data_text += "存在主键为空的脏数据\n"
            usname = user.USname
            usopenid2 = user.USopenid2
            ustelphone = user.UStelphone
            usheader = user.USheader
            usidentification = user.USidentification
            ustoagenttime = user.UStoAgentTime
            usgender = user.USgender
            usbirthday = user.USbirthday
            usintegral = user.USintegral
            uscontinuous = user.UScontinuous
            uslevel = user.USlevel
            uscommisionlevel = user.CommisionLevel
            usrealname = user.USrealname
            if not usopenid2:
                current_app.logger.info(usid + "异常用户，非法的openid")
                data_text += "{0},异常用户，非法的openid\n".format(usid)
            if "客官" in usname:
                if usheader != "用户头像":
                    current_app.logger.info(usid + "用户已授权登录，但数据未更改")
                    data_text += "{0},用户已授权登录，但数据未更改\n".format(usid)
                if ustelphone:
                    current_app.logger.info(usid + "用户异常手机认证")
                    data_text += "{0},用户异常手机认证\n".format(usid)
                if usidentification or usrealname:
                    current_app.logger.info(usid + "用户异常实名")
                    data_text += "{0},用户异常实名\n".format(usid)
                if ustoagenttime or uslevel != 1:
                    current_app.logger.info(usid + "用户异常成为分销商")
                    data_text += "{0},用户异常成为分销商\n".format(usid)
                if usgender or usbirthday:
                    current_app.logger.info(usid + "用户异常修改个人信息")
                    data_text += "{0},用户异常修改个人信息\n".format(usid)
                if usintegral != 0:
                    current_app.logger.info(usid + "用户非法获取星币")
                    data_text += "{0},用户非法获取星币\n".format(usid)
                if uscontinuous != 0:
                    current_app.logger.info(usid + "用户非法签到")
                    data_text += "{0},用户非法签到\n".format(usid)
                if uscommisionlevel != 1:
                    current_app.logger.info(usid + "用户非法升级")
                    data_text += "{0},用户非法升级\n".format(usid)
            ussupper1 = user.USsupper1
            ussupper2 = user.USsupper2
            ussupper3 = user.USsupper3
            uscommission1 = user.USCommission1
            uscommission2 = user.USCommission2
            uscommission3 = user.USCommission3
            if ussupper3:
                if not ussupper2 or not ussupper1:
                    current_app.logger.info(usid + "异常的分销体系，中间有断层")
                    data_text += "{0},异常的分销体系，中间有断层\n".format(usid)
                user_test = User.query.filter(User.USid == str(ussupper3). User.isdelete == 0).all()
                if not user_test:
                    current_app.logger.info(usid + "第三级分佣人员数据异常")
                    data_text += "{0},第三级分佣人员数据异常\n".format(usid)
            if ussupper2:
                if not ussupper1:
                    current_app.logger.info(usid + "异常的分销体系，中间有断层")
                    data_text += "{0},异常的分销体系，中间有断层\n".format(usid)
                user_test = User.query.filter(User.USid == str(ussupper2), User.isdelete == 0).all()
                if not user_test:
                    current_app.logger.info(usid + "第二级分佣人员数据异常")
                    data_text += "{0},第二级分佣人员数据异常\n".format(usid)
            if ussupper1:
                user_test = User.query.filter(User.USid == str(ussupper1), User.isdelete == 0).all()
                if not user_test:
                    current_app.logger.info(usid + "第一级分佣人员数据异常")
                    data_text += "{0},第一级分佣人员数据异常\n".format(usid)
            if uscommission1 or uscommission2 or uscommission3:
                current_app.logger.info(usid + "设置过非平台预定佣金比例")
                data_text += "{0},设置过非平台预定佣金比例\n".format(usid)
        current_app.logger.info(">>>>>>>>>>>>>>>>>>>>>>User test data end>>>>>>>>>>>>>>>>>>>>>>>>")
        return data_text