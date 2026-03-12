from sqlmodel import Session, select
from app.db.database import engine
from app.models.core_models import Rol, Empleado
from app.core.security import get_password_hash

def seed_bar_data():
    with Session(engine) as session:
        print("--- Poblando tablas originales del Bar ---")

        statement_rol = select(Rol).where(Rol.nombre == "Administrador")
        db_rol = session.exec(statement_rol).first()

        if not db_rol:
            db_rol = Rol(nombre="Administrador")
            session.add(db_rol)
            session.commit()
            session.refresh(db_rol)
            print(f"Rol 'Administrador' creado en la tabla Roles.")
        else:
            print("El Rol 'Administrador' ya existe.")

        statement_emp = select(Empleado).where(Empleado.email == "admin@bar.com")
        db_emp = session.exec(statement_emp).first()

        if not db_emp:
            nuevo_admin = Empleado(
                rol_id=db_rol.id,
                documento_identidad="001-0000000-1",
                nombre_completo="Admin Bar CORE",
                email="admin@bar.com",
                password_hash=get_password_hash("Intec2026*"),
                activo=True
            )
            session.add(nuevo_admin)
            session.commit()
            print(f"Empleado '{nuevo_admin.nombre_completo}' creado en la tabla Empleados.")
        else:
            print(f"El empleado administrador ya existe.")

if __name__ == "__main__":
    seed_bar_data()