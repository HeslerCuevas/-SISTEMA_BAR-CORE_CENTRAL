import bcrypt


def generar_hash_manual(password: str):
    # Convertir la contraseña a bytes
    pwd_bytes = password.encode('utf-8')

    # Generar la sal (salt) con 12 rounds (estándar de producción)
    salt = bcrypt.gensalt(rounds=12)

    # Generar el hash
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)

    # Decodificar a string para usar en SQL
    return hashed_password.decode('utf-8')


# --- CONFIGURACIÓN ---
mi_password = "12345"  # Escribe aquí la clave que quieras
print(f"Password: {mi_password}")
print(f"Hash para SQL: {generar_hash_manual(mi_password)}")