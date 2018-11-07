from planet.models import IdentifyingCode, User, UserCommission, UserLoginTime


class SUser():
    def get_identifyingcode_by_ustelphone(self, utel):
        return self.session.query(IdentifyingCode).filter(IdentifyingCode.ICtelphone == utel).first_()

    def get_user_by_ustelphone(self, utel):
        return self.session.query(User).filter(User.UStelphone == utel).first_()
