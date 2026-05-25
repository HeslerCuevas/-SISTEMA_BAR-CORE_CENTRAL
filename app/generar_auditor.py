import bcrypt

def generar_hash_consultor(password: str):
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')

clave_plana = "consultor123"
print(f"Password: {clave_plana}")
print(f"Hash para SQL: {generar_hash_consultor(clave_plana)}")