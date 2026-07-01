import pandas as pd
import os
from base_datos import guardar_cuenta_puc

def ejecutar_carga():
    # Obtener la ruta donde está guardado este archivo script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    archivo_csv = os.path.join(base_dir, 'Plan_De_Cuentas_Actualizado.csv')
    
    # Verificar si el archivo existe
    if not os.path.exists(archivo_csv):
        print(f"Error: No se encontró el archivo en: {archivo_csv}")
        return

    # Leer el archivo usando la ruta completa
    df = pd.read_csv(archivo_csv)
    
    print(f"Iniciando carga de {len(df)} cuentas...")
    
    # Iterar sobre el archivo y guardar fila por fila
    for _, fila in df.iterrows():
        datos = {
            'codigo': str(fila['Codigo_Cuenta']),
            'nombre': fila['Nombre_Cuenta'],
            'nivel': int(fila['Nivel']),
            'padre': str(fila['Codigo_Padre']),
            'naturaleza': fila['Naturaleza'],
            'es_movimiento': bool(fila['Es_Movimiento'])
        }
        guardar_cuenta_puc(datos)
        
    print("¡Proceso completado con éxito! El PUC ha sido cargado en la base de datos.")

if __name__ == "__main__":
    ejecutar_carga()
