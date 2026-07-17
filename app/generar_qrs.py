import qrcode
import os

URL_BASE = "https://nocturnal-bar.app/scan"
SUCURSAL_ID = 1
CANTIDAD_MESAS = 15

carpeta_qrs = "qrs_mesas"
if not os.path.exists(carpeta_qrs):
    os.makedirs(carpeta_qrs)

print(f"Generating QR codes for {CANTIDAD_MESAS} tables...")

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

    img = qr.make_image(fill_color="black", back_color="white")
    nombre_archivo = f"{carpeta_qrs}/QR_Sucursal_{SUCURSAL_ID}_Mesa_{mesa_id}.png"
    img.save(nombre_archivo)

print("Process complete! Check the 'qrs_mesas' folder.")
