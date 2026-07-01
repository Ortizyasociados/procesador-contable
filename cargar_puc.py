import pandas as pd
import os
from base_datos import guardar_cuenta_puc

def ejecutar_carga():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    archivo_csv = os.path.join(base_dir, 'Plan_de_Cuentas_Actualizado.csv')
    
    if not os.path.exists(archivo_csv):
        print(f"Error: No se encontró el archivo: {archivo_csv}")
        return

    # Leer archivo
    df = pd.read_csv(archivo_csv)
    
    # Esto imprimirá las columnas reales para que salgamos de dudas si vuelve a fallar
    print(f"Columnas detectadas en el archivo: {list(df.columns)}")
    
    print(f"Iniciando carga de {len(df)} cuentas...")
    
    for _, fila in df.iterrows():
        # Usamos .get() para evitar errores si el nombre no es exacto
        # Si esto falla, el error nos dirá exactamente cuál columna falta
        datos = {
            'codigo': fila[df.columns[0]], # Primera columna
            'nombre': fila[df.columns[1]], # Segunda columna
            'nivel': int(fila[df.columns[2]]),
            'padre': str(fila[df.columns[3]]),
            'naturaleza': fila[df.columns[4]],
            'es_movimiento': bool(fila[df.columns[5]])
        }
        guardar_cuenta_puc(datos)
        
    print("¡Proceso completado con éxito!")

if __name__ == "__main__":
    ejecutar_carga()
