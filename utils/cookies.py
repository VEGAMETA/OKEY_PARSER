import re
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding


def _get_cookie_spsc_from_encrypted(key, encrypted_data) -> str:
    pem_key = key
    encrypted_data = bytes.fromhex(encrypted_data)
    private_key = serialization.load_pem_private_key(pem_key.encode(), password=None)
    decrypted_data = private_key.decrypt(encrypted_data, padding.PKCS1v15())
    return decrypted_data.decode("utf-8")


def _get_rsa_key_and_encrypted_spsc_from_html(html) -> tuple[str, str] | None:
    private_key_pattern = re.compile(r'-{5,}([\s\S]*?)\n([\s\S]*?)-{5,}\n')
    hex_string_pattern = re.compile(r'"([0-9a-fA-F]{256})"')
    private_key_match = private_key_pattern.search(html)
    hex_string_match = hex_string_pattern.search(html)
    rsa_private_key, hex_string = "", ""
    if private_key_match:
        rsa_private_key = private_key_match.group(0)
    if hex_string_match:
        hex_string = hex_string_match.group(1)
    return rsa_private_key, hex_string


def _get_spid_from_html(html) -> str:
    spid_pattern = re.compile(r'spid=([^\"]+)')
    spid_match = spid_pattern.search(html)
    spid = ""
    if spid_match:
        spid = spid_match.group(1)
    return spid


def get_spid_spsc_cookies_from_html(html) -> tuple[str, str]:
    spid = _get_spid_from_html(html)
    spsc = _get_cookie_spsc_from_encrypted(*_get_rsa_key_and_encrypted_spsc_from_html(html))
    return spid, spsc
