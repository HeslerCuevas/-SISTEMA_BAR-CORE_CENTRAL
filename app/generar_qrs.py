import qrcode
import os

# Configuración
URL_BASE = "https://nocturnal-bar.app/scan"
SUCURSAL_ID = 1
CANTIDAD_MESAS = 15  # Cambia esto por la cantidad de mesas que tengas

carpeta_qrs = "qrs_mesas"
if not os.path.exists(carpeta_qrs):
    os.makedirs(carpeta_qrs)

print(f"Generando códigos QR para {CANTIDAD_MESAS} mesas...")

for mesa_id in range(1, CANTIDAD_MESAS + 1):
    data = f"{URL_BASE}?sucursal={SUCURSAL_ID}&mesa={mesa_id}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # 3. Crear y guardar la imagen
    img = qr.make_image(fill_color="black", back_color="white")
    nombre_archivo = f"{carpeta_qrs}/QR_Sucursal_{SUCURSAL_ID}_Mesa_{mesa_id}.png"
    img.save(nombre_archivo)

print("¡Proceso terminado! Revisa la carpeta 'qrs_mesas'.")