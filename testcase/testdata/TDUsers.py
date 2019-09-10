from flask import current_app
from planet.models.user import User, UserLoginTime, Admin, UserCommission
from planet.models.product import Supplizer
from planet.models.trade import OrderMain, OrderPart

class TDUsers():

    def test_user_data(self):
        """
        测试用户数据
        :return:
        """
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
                user_test = User.query.filter(User.USid == str(ussupper3), User.isdelete == 0).all()
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
        if data_text == "":
            return "No error data"
        return data_text

    def test_userlogintime_data(self):
        """
        测试用户登录时间数据
        :return:
        """
        data_text = ""
        current_app.logger.info(">>>>>>>>>>>>>>>>>>>>>>UserLoginTime test data start>>>>>>>>>>>>>>>>>>>>>>>>")
        all_user = UserLoginTime.query.filter(UserLoginTime.isdelete == 0).all()
        for user in all_user:
            ultid = user.ULTid
            usid = user.USid
            ustip = user.USTip
            ultype = user.ULtype
            if not usid:
                data_text += "{0}, 异常的数据写入，安全警告\n".format(ultid)
            if not ustip:
                data_text += "{0}, 未知区域数据写入，安全警告\n".format(ultid)
            if int(ultype) == 1:
                test_user = User.query.filter(User.USid == usid, User.isdelete == 0)
                if not test_user:
                    data_text += "{0}, 异常用户{1}数据\n".format(ultid, usid)
            elif int(ultype) == 2:
                test_user = Admin.query.filter(Admin.ADid == usid, Admin.isdelete == 0)
                if not test_user:
                    data_text += "{0}, 异常管理员{1}数据\n".format(ultid, usid)
        current_app.logger.info(">>>>>>>>>>>>>>>>>>>>>>UserLoginTime test data end>>>>>>>>>>>>>>>>>>>>>>>>")
        if data_text == "":
            return "No error data"
        return data_text

    def test_usercommission_data(self):
        """
        测试佣金数据
        :return:
        """
        data_text = ""
        current_app.logger.info(">>>>>>>>>>>>>>>>>>>>>>UserLoginTime test data start>>>>>>>>>>>>>>>>>>>>>>>>")
        all_user = UserCommission.query.filter(UserCommission.isdelete == 0)
        for user in all_user:
            ucid = user.UCid
            uccommission = user.UCcommission
            usid = user.USid
            commisionfor = user.CommisionFor
            fromusid = user.FromUsid
            ucstatus = user.UCstatus
            uctype = user.UCtype
            ucendtime = user.UCendTime
            prtitle = user.PRtitle
            skupic = user.SKUpic
            omid = user.OMid
            opid = user.OPid
            if float(uccommission) < 0:
                if commisionfor == 0 or usid == "0":
                    data_text += "{0},佣金不合法\n".format(ucid)
            if commisionfor == 0:
                if usid != "0":
                    data_text += "{0},平台状态异常\n".format(ucid)
            elif commisionfor == 10:
                test_user = Supplizer.query.filter(Supplizer.isdelete == 0, Supplizer.SUid == usid).all()
                if not test_user:
                    data_text += "{0},佣金发放缺失对应供应商{1}\n".format(ucid, usid)
            elif commisionfor == 20:
                test_user = User.query.filter(User.isdelete == 0, User.USid == usid).all()
                if not test_user:
                    data_text += "{0},佣金发放缺失对应用户{1}\n".format(ucid, usid)
            else:
                data_text += "{0}，身份状态异常\n".format(ucid)
            test_user = User.query.filter(User.isdelete == 0, User.USid == fromusid).all()
            if not test_user:
                data_text += "{0}, 佣金来源用户{1}缺失\n".format(ucid, fromusid)
            if ucstatus == -1:
                data_text += "{0}，佣金状态异常\n".format(ucid)
            if ucstatus not in [-1, 0, 1, 2]:
                data_text += "{0}, 佣金状态不合法\n".format(ucid)
            if uctype not in [0, 1, 2]:
                data_text += "{0}, 收益类型不合法\n".format(ucid)
            if not ucendtime and uctype == 2:
                data_text += "{0}, 押金不合法\n".format(ucid)
            if not prtitle or not skupic:
                data_text += "{0}, 商品数据异常\n".format(ucid)
            if not omid or not opid:
                data_text += "{0}, 订单数据异常\n".format(ucid)
            test_ordermain = OrderMain.query.filter(OrderMain.isdelete == 0, OrderMain.OMid == omid).all()
            test_orderpart = OrderPart.query.filter(OrderPart.isdelete == 0, OrderPart.OPid == opid).all()
            if not test_ordermain:
                data_text += "{0}, 主单{1}数据不存在\n".format(ucid, omid)
            if not test_orderpart:
                data_text += "{0}, 副单{1}数据不存在\n".format(ucid, opid)
        current_app.logger.info(">>>>>>>>>>>>>>>>>>>>>>UserLoginTime test data end>>>>>>>>>>>>>>>>>>>>>>>>")
        if data_text == "":
            return "No error data"
        return data_text