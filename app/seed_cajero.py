import bcrypt

def generar_hash_manual(password: str):
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')

mi_password = "12345"
print(f"Password: {mi_password}")
print(f"Hash para SQL: {generar_hash_manual(mi_password)}")