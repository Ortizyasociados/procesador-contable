import pandas as pd
import os
import numpy as np
from base_datos import guardar_cuenta_puc

def ejecutar_carga():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    archivo_csv = os.path.join(base_dir, 'Plan_de_Cuentas_Actualizado.csv')
    
    if not os.path.exists(archivo_csv):
        print(f"Error: No se encontró el archivo: {archivo_csv}")
        return

    # Leer archivo
    df = pd.read_csv(archivo_csv)
    
    # Limpiamos los datos: convertimos valores nulos (NaN) a 0 o texto vacío
    df = df.replace({np.nan: None})
    
    print(f"Iniciando carga de {len(df)} cuentas...")
    
    for _, fila in df.iterrows():
        try:
            # Aseguramos tipos de datos: si Nivel es None, ponemos 0
            nivel = int(fila[df.columns[2]]) if fila[df.columns[2]] is not None else 0
            
            datos = {
                'codigo': str(fila[df.columns[0]]),
                'nombre': str(fila[df.columns[1]]),
                'nivel': nivel,
                'padre': str(fila[df.columns[3]]) if fila[df.columns[3]] is not None else "",
                'naturaleza': str(fila[df.columns[4]]) if fila[df.columns[4]] is not None else "",
                'es_movimiento': bool(fila[df.columns[5]])
            }
            guardar_cuenta_puc(datos)
        except Exception as e:
            print(f"Error en fila {fila[0]}: {e}")
            continue
        
    print("¡Proceso completado con éxito! El PUC ha sido cargado en la base de datos.")

if __name__ == "__main__":
    ejecutar_carga()
