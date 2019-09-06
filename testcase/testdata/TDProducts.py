from planet.models.product import Supplizer, Products, ProductCategory, ProductBrand
from flask import current_app
from planet.models.user import Admin

class TDProducts():

    def test_products_data(self):
        data_text = ""
        current_app.logger.info(">>>>>>>>>>>>>>>>>>>>>>User test data start>>>>>>>>>>>>>>>>>>>>>>>>")
        all_product = Products.query.filter(Products.isdelete == 0).all()
        for product in all_product:
            prid = product.PRid
            prtitle = product.PRtitle
            prprice = product.PRprice
            prlineprice = product.PRlinePrice
            prfreight = product.PRfreight
            prstocks = product.PRstocks
            prsalesvalue = product.PRsalesValue
            prstatus = product.PRstatus
            prmainpic = product.PRmainpic
            prattribute = product.PRattribute
            pcid = product.PCid
            pbid = product.PBid
            prdesc = product.PRdesc
            prremarks = product.PRremarks
            prfrom = product.PRfrom
            prdescription = product.PRdescription
            createrid = product.CreaterId
            prfeatured = product.PRfeatured
            praveragescore = product.PRaverageScore
            prcode = product.PRcode
            prpromotion = product.PRpromotion
            if prprice <= 0:
                data_text += "{0}, 商品价格错误\n".format(prid)
            if prfreight != 0:
                data_text += "{0}, 商品运费异常设置\n".format(prid)
            if prlineprice < 0:
                data_text += "{0}, 商品划线价格错误\n".format(prid)
            if prstocks < 0:
                data_text += "{0}, 商品超卖\n".format(prid)
            if prsalesvalue < 0:
                data_text += "{0}, 商品销量异常\n".format(prid)
            if prstatus not in [0, 10, 40, 60]:
                data_text += "{0}, 商品状态异常\n".format(prid)
            if not prmainpic or not prattribute or not prdesc or not prpromotion:
                data_text += "{0}, 商品图片缺失\n".format(prid)
            if praveragescore > 10 or prsalesvalue < 0:
                data_text += "{0}, 商品平均分错误\n".format(prid)
            if pcid:
                productcategory = ProductCategory.query.filter(ProductCategory.PCid == pcid, ProductCategory.isdelete == 0).first()
                if not productcategory:
                    data_text += "{0}, 商品分类异常\n".format(prid)
            if prfrom == 0:
                productbrand = ProductBrand.query.filter(ProductBrand.PBid == pbid, ProductBrand.isdelete == 0).first()
                suid = productbrand.SUid
                if suid:
                    data_text += "{0}, 商品归属错误\n".format(prid)
                admin = Admin.query.filter(Admin.isdelete == 0, Admin.ADid == createrid).first()
                if not admin:
                    data_text += "{0}, 商品创建者{1}不存在\n".format(prid, createrid)
            elif prfrom == 10:
                productbrand = ProductBrand.query.filter(ProductBrand.PBid == pbid, ProductBrand.isdelete == 0, ProductBrand.SUid == createrid).first()
                if not productbrand:
                    data_text += "{0}, 商品供应商{1}异常\n".format(prid, createrid)
            else:
                data_text += "{0}, 商品来源异常\n".format(prid)
        current_app.logger.info(">>>>>>>>>>>>>>>>>>>>>>User test data end>>>>>>>>>>>>>>>>>>>>>>>>")
        if data_text == "":
            return "No error data"
        return data_text