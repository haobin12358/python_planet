from planet.common.base_resource import Resource
from planet.control.CApproval import CApproval


class Aapproval(Resource):
    def __init__(self):
        self.approval = CApproval()

    def post(self, approval):
        apis = {
            'add_permission': self.approval.add_permission,
            'deal_approval': self.approval.deal_approval,
            'create': self.approval.create,
            'add_permissionitems': self.approval.add_permissionitems,
            'add_permission_type': self.approval.add_permission_type,
            # 'add_permission': self.approval.add_permission,
            # 'deal_approval': self.approval.deal_approval,
            'cancel': self.approval.cancel,
            'add_adminpermission': self.approval.add_adminpermission,
            'delete_permission': self.approval.delete_permission,
            'add_pi_and_pe_and_ap': self.approval.add_pi_and_pe_and_ap,
            # 'create': self.approval.create,
        }
        return apis

    def get(self, approval):
        apis = {
            'get_permission_type_list': self.approval.get_permission_type_list,
            'get_permission_list': self.approval.get_permission_list,
            'get_permission_admin_list': self.approval.get_permission_admin_list,
            'get_dealing_approval': self.approval.get_dealing_approval,
            'get_approval_list': self.approval.get_approval_list,
            'get_all_permissiontype': self.approval.get_all_permissiontype,
            'get_permissionitem': self.approval.get_permissionitem,
            'get_permissiontype': self.approval.get_permissiontype,
            'get_avstatus': self.approval.get_avstatus,
            # 'get_submit_approval': self.approval.get_submit_approval,

            'get_approvalnotes': self.approval.get_approvalnotes,
            'list_approval_notes': self.approval.list_approval_notes,
        }
        return apis

