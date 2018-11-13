from sqlalchemy import and_, or_
from planet.common.base_service import SBase
from planet.models.approval import Approval, Permission



class SApproval(SBase):

    def get_permission_by_type_level(self, petype, pelevel):
        return self.session.query(Permission).filter_by_(PEtype=petype, PELevel=pelevel).order_by(Permission.createtime.desc()).all()

    def get_permission_by_id(self, peid):
        return self.session.query(Permission).filter_by_(PEid=peid).first()
