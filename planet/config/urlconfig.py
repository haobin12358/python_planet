# *- coding:utf8 *-
get_user_info = "https://api.weixin.qq.com/sns/userinfo?access_token={0}&openid={1}&lang=zh_CN"
get_access_toke = "https://api.weixin.qq.com/sns/oauth2/access_token?appid={0}&secret={1}&code={2}&grant_type=authorization_code"
get_jsapi = "https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token={0}&type=jsapi"
# get_server_access_token = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=wxe8e8f6b9351d3587&secret=b89e22f046d33b39c7a4afa485e661dc"
get_server_access_token = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=wx8206635590c9cc0e&secret=ba8c532bfd8e7390e3cfc91ac17c0472"
signature_str = "jsapi_ticket={jsapi_ticket}&noncestr={noncestr}&timestamp={timestamp}&url={url}"
get_subscribe = "https://api.weixin.qq.com/cgi-bin/user/info?access_token={0}&openid={1}&lang=zh_CN"
