import base64
import os

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.conf import settings
from django.db import models

# AES works on 128-bit blocks regardless of key size, so the IV and padding
# block are both 16 bytes.
BLOCK_SIZE_BITS = algorithms.AES.block_size
IV_LENGTH = BLOCK_SIZE_BITS // 8


class EncryptedTextField(models.TextField):
    """A TextField that transparently encrypts its value at rest.

    Values are encrypted with AES-256-CBC before hitting the database and
    decrypted on the way back, so application code reads and writes plaintext
    while the stored column only ever holds a base64 blob of IV + ciphertext.
    """

    def _cipher(self, iv):
        return Cipher(algorithms.AES(settings.ENCRYPTION_KEY), modes.CBC(iv))

    def _encrypt(self, plaintext):
        # A fresh random IV per value means identical plaintexts do not produce
        # identical ciphertexts, which would otherwise leak equality.
        iv = os.urandom(IV_LENGTH)
        padder = padding.PKCS7(BLOCK_SIZE_BITS).padder()
        padded = padder.update(plaintext.encode('utf-8')) + padder.finalize()
        encryptor = self._cipher(iv).encryptor()
        ciphertext = encryptor.update(padded) + encryptor.finalize()
        return base64.b64encode(iv + ciphertext).decode('ascii')

    def _decrypt(self, stored):
        raw = base64.b64decode(stored)
        iv, ciphertext = raw[:IV_LENGTH], raw[IV_LENGTH:]
        decryptor = self._cipher(iv).decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(BLOCK_SIZE_BITS).unpadder()
        return (unpadder.update(padded) + unpadder.finalize()).decode('utf-8')

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        # Leave NULL and empty strings untouched; there is nothing to protect and
        # encrypting them would only complicate empty-value handling.
        if value is None or value == '':
            return value
        return self._encrypt(value)

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value
        return self._decrypt(value)
