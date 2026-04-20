from sqlmodel import Session, select
from app.db.database import engine
from app.models.core_models import Rol, Empleado, Sucursal
from app.core.security import get_password_hash

def seed_bar_data():
    with Session(engine) as session:
        print("--- Poblando tablas originales del Bar ---")

        statement_sucursal = select(Sucursal).where(Sucursal.nombre == "Casa Matriz")
        db_sucursal = session.exec(statement_sucursal).first()

        if not db_sucursal:
            db_sucursal = Sucursal(
                nombre="Casa Matriz",
                direccion="Sede Principal Bar & Lounge",
                activo=True
            )
            session.add(db_sucursal)
            session.commit()
            session.refresh(db_sucursal)
            print(f"Sucursal 'Casa Matriz' creada.")
        else:
            print("La Sucursal 'Casa Matriz' ya existe.")

        statement_rol = select(Rol).where(Rol.nombre == "Administrador")
        db_rol = session.exec(statement_rol).first()

        if not db_rol:
            db_rol = Rol(nombre="Administrador")
            session.add(db_rol)
            session.commit()
            session.refresh(db_rol)
            print(f"Rol 'Administrador' creado.")
        else:
            print("El Rol 'Administrador' ya existe.")

        statement_emp = select(Empleado).where(Empleado.email == "admin@bar.com")
        db_emp = session.exec(statement_emp).first()

        if not db_emp:
            nuevo_admin = Empleado(
                rol_id=db_rol.id,
                sucursal_id=db_sucursal.id,
                documento_identidad="001-0000000-1",
                nombre_completo="Admin Bar CORE",
                email="admin@bar.com",
                password_hash=get_password_hash("Intec2026*"),
                activo=True
            )
            session.add(nuevo_admin)
            try:
                session.commit()
                print(f"Empleado '{nuevo_admin.nombre_completo}' creado exitosamente.")
            except Exception as e:
                session.rollback()
                print(f"Error al crear el empleado: {e}")
        else:
            print(f"El empleado administrador ya existe.")

if __name__ == "__main__":
    seed_bar_data()