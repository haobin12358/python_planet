# from planet.common.base_service import SBase
from planet.models import IdentifyingCode, User, UserCommission, UserLoginTime, UserAddress, AddressProvince, \
    AddressCity, AddressArea, UserMedia, IDCheck, Admin, AdminNotes
from sqlalchemy import or_, and_


class SUser():
    def get_identifyingcode_by_ustelphone(self, utel):
        return self.session.query(IdentifyingCode).filter(
            IdentifyingCode.ICtelphone == utel, IdentifyingCode.isdelete == False).order_by(
            IdentifyingCode.createtime.desc()).first_()

    def get_user_by_ustelphone(self, utel):
        return self.session.query(User).filter(User.UStelphone == utel, User.isdelete == False).first_()

    def get_user_by_id(self, usid):
        return self.session.query(User).filter(User.USid == usid, User.isdelete == False).first_('用户不存在')

    def get_user_by_tel(self, ustel):
        return self.session.query(User).filter(User.UStelphone == ustel, User.isdelete == False).first_()

    def get_useraddress_by_usid(self, usid):
        return self.session.query(UserAddress).filter(UserAddress.USid == usid, UserAddress.isdelete == False
                                                      ).order_by(UserAddress.UAdefault.desc()).all_with_page()

    def get_useraddress_by_filter(self, uafilter):
        """根据条件获取地址"""
        return self.session.query(UserAddress).filter_by(**uafilter).first()

    def get_province(self):
        """获取所有省份"""
        return self.session.query(AddressProvince).all()

    def get_citylist_by_provinceid(self, provinceid):
        """根据省份编号获取城市列表"""
        return self.session.query(AddressCity).filter(AddressCity.APid == provinceid).all()

    def get_arealist_by_cityid(self, cityid):
        """通过城市编号获取区县列表"""
        return self.session.query(AddressArea).filter(AddressArea.ACid == cityid).all()

    def get_addressinfo_by_areaid(self, areaid):
        """通过区县id 获取具体的三级地址"""
        return self.session.query(AddressArea, AddressCity, AddressProvince).filter(
            AddressArea.ACid == AddressCity.ACid, AddressCity.APid == AddressProvince.APid).filter(
            AddressArea.AAid == areaid).first_('aaid错误，没有该区域信息')

    def get_usermedia(self, usid, umtype):
        """获取用户身份证图片"""
        return self.session.query(UserMedia).filter(
            UserMedia.USid == usid, UserMedia.UMtype==umtype, UserMedia.isdelete == False).order_by(
            UserMedia.createtime.desc()).first()

    def get_idcheck_by_name_code(self, name, idcode):
        return self.session.query(IDCheck).filter(
            IDCheck.IDCcode == idcode,
            IDCheck.IDCname == name,
            IDCheck.IDCerrorCode != 80008,
            IDCheck.isdelete == False
        ).first_()

    def get_admin_by_name(self, adname):
        return self.session.query(Admin).filter_(Admin.ADname == adname).first()

    def get_admin_by_id(self, adid):
        return self.session.query(Admin).filter(Admin.ADid == adid).first_('不存在该管理员')

    # update 操作

    def update_useraddress_by_filter(self, uafilter, uainfo):
        """更新地址"""
        return self.session.query(UserAddress).filter_by(**uafilter).update(uainfo)

    def update_user_by_filter(self, us_and_filter, us_or_filter, usinfo):
        return self.session.query(User).filter(
            and_(*us_and_filter), or_(*us_or_filter), User.isdelete == False).update(usinfo)

    def update_admin_by_filter(self, ad_and_filter, ad_or_filter, adinfo):
        return self.session.query(Admin).filter_(
            and_(*ad_and_filter), or_(*ad_or_filter), Admin.isdelete == False).update(adinfo)

    # 逻辑delete 操作
    def delete_usemedia_by_usid(self, usid):
        self.session.query(UserMedia).filter(UserMedia.USid == usid).delete_()
