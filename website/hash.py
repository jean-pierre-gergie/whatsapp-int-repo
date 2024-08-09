import hashlib

pwd = '123456'

pwd_bytes = pwd.encode('utf-8')
hash_object = hashlib.sha256(pwd_bytes)
hash_digest = hash_object.hexdigest()

print(hash_digest)
