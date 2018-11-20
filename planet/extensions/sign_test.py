# -*- coding: utf-8 -*-
import base64

from Crypto.Hash import SHA
from Crypto.Signature import PKCS1_v1_5 as Signature_pkcs1_v1_5
from Crypto.PublicKey import RSA
with open('/home/wukt/project/python_planet/pem2/rsa_private_key.pem', 'r') as rf:
    key = rf.read()
    print(key)
rsakey = RSA.importKey(key)

signer = Signature_pkcs1_v1_5.new(rsakey)
digest = SHA.new()
digest.update('a=123'.encode())
sign = signer.sign(digest)
signature = base64.b64encode(sign).decode()
print(signature)
