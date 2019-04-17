from planet.common.base_resource import Resource
from planet.control.CExcel import CExcel


class AExcel(Resource):
    def __init__(self):
        self.cexcel = CExcel()

    def get(self, excel):
        apis = {
            'download': self.cexcel.download
        }
        return apis

    def post(self, excel):
        apis = {
            'upload': self.cexcel.upload_products_file,
            'delivery': self.cexcel.upload_delivery_file,
        }
        return apis
