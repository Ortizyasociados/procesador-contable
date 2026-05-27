import streamlit as st
import pandas as pd
import zipfile
import io
import xml.etree.ElementTree as ET

ns = {
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
}

def obtener_valor(elemento, ruta, index=0):
    res = elemento.findall(ruta, ns)
    return res[index].text if res and index < len(res) else "0"

st.title("Procesador de Facturas XML")

uploaded_file = st.file_uploader("Sube tu archivo ZIP", type=["zip"])

if uploaded_file is not None:
    data_facturas = []
    with zipfile.ZipFile(uploaded_file) as z:
        for nombre_xml in z.namelist():
            if nombre_xml.endswith('.xml'):
                contenido = z.read(nombre_xml).decode('utf-8')
                root = ET.fromstring(contenido if '<Invoice' not in contenido else contenido[contenido.find('<Invoice'):contenido.rfind('</Invoice>')+10])
                item = {
                    "Numero": obtener_valor(root, './/cbc:ID'),
                    "Proveedor": obtener_valor(root, './/cac:AccountingSupplierParty//cbc:RegistrationName'),
                    "Total": float(obtener_valor(root, './/cac:LegalMonetaryTotal/cbc:PayableAmount'))
                }
                data_facturas.append(item)
    
    df = pd.DataFrame(data_facturas)
    
    # Esta es la única línea modificada para que la tabla no se oculte
    st.dataframe(df, use_container_width=True)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    st.download_button("Descargar Excel", data=output.getvalue(), file_name="Reporte.xlsx")
