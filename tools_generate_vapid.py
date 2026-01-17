from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

priv_num = private_key.private_numbers().private_value.to_bytes(32, "big")
pub_nums = public_key.public_numbers()
pub_bytes = b"\x04" + pub_nums.x.to_bytes(32, "big") + pub_nums.y.to_bytes(32, "big")

print("VAPID_PRIVATE_KEY=", b64url(priv_num))
print("VAPID_PUBLIC_KEY=", b64url(pub_bytes))
