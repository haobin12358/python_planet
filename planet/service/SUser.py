from planet.models import IdentifyingCode, User, UserCommission, UserLoginTime, UserAddress, AddressProvince, \
    AddressCity, AddressArea


class SUser():
    def get_identifyingcode_by_ustelphone(self, utel):
        return self.session.query(IdentifyingCode).filter(IdentifyingCode.ICtelphone == utel).first_()

    def get_user_by_ustelphone(self, utel):
        return self.session.query(User).filter(User.UStelphone == utel).first_()

    def get_user_by_id(self, usid):
        return self.session.query(User).filter(User.USid == usid).first_('用户不存在')

    def get_useraddress_by_usid(self, usid):
        return self.session.query(UserAddress).filter(UserAddress.USid == usid).all_with_page()

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
            AddressArea.AAid == areaid).all()
