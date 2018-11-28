from planet.common.base_service import SBase
from planet.models import IdentifyingCode, User, UserCommission, UserLoginTime, UserAddress, AddressProvince, \
    AddressCity, AddressArea, UserMedia, IDCheck, Admin, AdminNotes, UserIntegral
from sqlalchemy import or_, and_, extract


class SUser(SBase):

    def get_ucmonth_by_usid(self, usid, today):
        return UserCommission.query.filter(
            UserCommission.USid == usid, UserCommission.UCstatus == 1,
            extract('month', UserCommission.createtime) == today.month,
            extract('year', UserCommission.createtime) == today.year,
        ).all()

    def get_ucall_by_usid(self, usid):
        return UserCommission.query.filter(
            UserCommission.USid == usid, UserCommission.UCstatus == 1
        ).all()

    def get_identifyingcode_by_ustelphone(self, utel):
        return IdentifyingCode.query.filter(
            IdentifyingCode.ICtelphone == utel, IdentifyingCode.isdelete == False).order_by(
            IdentifyingCode.createtime.desc()).first_()

    def get_user_by_ustelphone(self, utel):
        return User.query.filter(User.UStelphone == utel, User.isdelete == False).first_()

    def get_user_by_id(self, usid):
        return User.query.filter(User.USid == usid, User.isdelete == False).first_('用户不存在')

    def get_user_by_tel(self, ustel):
        return User.query.filter(User.UStelphone == ustel, User.isdelete == False).first_()

    def get_useraddress_by_usid(self, usid):
        return UserAddress.query.filter(UserAddress.USid == usid, UserAddress.isdelete == False
                                                      ).order_by(UserAddress.UAdefault.desc()).all_with_page()

    def get_useraddress_by_filter(self, uafilter):
        """根据条件获取地址"""
        return UserAddress.query.filter_by(**uafilter).first()

    def get_province(self):
        """获取所有省份"""
        return AddressProvince.query.all()

    def get_citylist_by_provinceid(self, provinceid):
        """根据省份编号获取城市列表"""
        return AddressCity.query.filter(AddressCity.APid == provinceid).all()

    def get_arealist_by_cityid(self, cityid):
        """通过城市编号获取区县列表"""
        return AddressArea.query.filter(AddressArea.ACid == cityid).all()

    def get_addressinfo_by_areaid(self, areaid):
        """通过区县id 获取具体的三级地址"""
        return self.session.query(AddressArea, AddressCity, AddressProvince).filter(
            AddressArea.ACid == AddressCity.ACid, AddressCity.APid == AddressProvince.APid).filter(
            AddressArea.AAid == areaid).first_('aaid错误，没有该区域信息')

    def get_usermedia(self, usid, umtype):
        """获取用户身份证图片"""
        return UserMedia.query.filter(
            UserMedia.USid == usid, UserMedia.UMtype==umtype, UserMedia.isdelete == False).order_by(
            UserMedia.createtime.desc()).first()

    def get_idcheck_by_name_code(self, name, idcode):
        return IDCheck.query.filter(
            IDCheck.IDCcode == idcode,
            IDCheck.IDCname == name,
            IDCheck.IDCerrorCode != 80008,
            IDCheck.isdelete == False
        ).first_()

    def get_admin_by_name(self, adname):
        return Admin.query.filter_(Admin.ADname == adname).first()

    def get_admin_by_id(self, adid):
        return Admin.query.filter(Admin.ADid == adid).first_('不存在该管理员')

    def get_admins(self):
        return Admin.query.filter(Admin.isdelete == False).all_with_page()
    # update 操作

    def update_useraddress_by_filter(self, uafilter, uainfo):
        """更新地址"""
        return UserAddress.query.filter_by(**uafilter).update(uainfo)

    def update_user_by_filter(self, us_and_filter, us_or_filter, usinfo):
        return User.query().filter(
            and_(*us_and_filter), or_(*us_or_filter), User.isdelete == False).update(usinfo)

    def update_admin_by_filter(self, ad_and_filter, ad_or_filter, adinfo):
        return Admin.query.filter_(
            and_(*ad_and_filter), or_(*ad_or_filter), Admin.isdelete == False).update(adinfo)

    # 逻辑delete 操作
    def delete_usemedia_by_usid(self, usid):
        UserMedia.query.filter(UserMedia.USid == usid).delete_()
