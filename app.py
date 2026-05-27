import streamlit as st
import pandas as pd
import zipfile
import io
import xml.etree.ElementTree as ET

# Configuración para aprovechar todo el ancho de la pantalla
st.set_page_config(layout="wide")

ns = {
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
}

def obtener_valor(elemento, ruta, index=0):
    res = elemento.findall(ruta, ns)
    return res[index].text if res and index < len(res) else "0"

def obtener_telefono(root):
    tel = obtener_valor(root, './/cac:AccountingCustomerParty//cac:Party//cac:Contact//cbc:Telephone')
    if tel == "0":
        tel = obtener_valor(root, './/cac:AccountingCustomerParty//cac:Contact//cbc:Telephone')
    return tel

st.title("Procesador de Facturas XML")
uploaded_files = st.file_uploader("Sube tus archivos ZIP", type=["zip"], accept_multiple_files=True)

if uploaded_files:
    data_facturas = []
    
    for uploaded_file in uploaded_files:
        with zipfile.ZipFile(uploaded_file) as z:
            for nombre_xml in z.namelist():
                if nombre_xml.endswith('.xml'):
                    contenido = z.read(nombre_xml).decode('utf-8')
                    
                    # Tu lógica de parseo original
                    if '<Invoice' in contenido:
                        xml_text = contenido[contenido.find('<Invoice'):contenido.rfind('</Invoice>')+10]
                        root = ET.fromstring(xml_text)
                    else:
                        root = ET.fromstring(contenido)
                    
                    numero = obtener_valor(root, './/cbc:ID')
                    fecha_emision = obtener_valor(root, './/cbc:IssueDate')
                    fecha_vencimiento = obtener_valor(root, './/cbc:DueDate')
                    if fecha_vencimiento == "0":
                        fecha_vencimiento = obtener_valor(root, './/cbc:PaymentDueDate')
                    
                    tipo_pago = "CRÉDITO" if (fecha_vencimiento != "0" and fecha_vencimiento != fecha_emision) else "CONTADO"
                    descripciones = [d.text for d in root.findall('.//cac:InvoiceLine/cac:Item/cbc:Description', ns) if d.text]

                    # Tu diccionario original
                    item = {
                        "Numero": numero,
                        "Fecha": fecha_emision,
                        "Fecha_Vencimiento": fecha_vencimiento,
                        "Tipo_Pago": tipo_pago,
                        "Proveedor": obtener_valor(root, './/cac:AccountingSupplierParty//cbc:RegistrationName'),
                        "NIT_Proveedor": obtener_valor(root, './/cac:AccountingSupplierParty//cbc:CompanyID'),
                        "Direccion_Proveedor": obtener_valor(root, './/cac:AccountingSupplierParty//cac:Party//cac:PhysicalLocation//cac:Address//cac:AddressLine//cbc:Line'),
                        "Cliente": obtener_valor(root, './/cac:AccountingCustomerParty//cbc:RegistrationName'),
                        "NIT_Cliente": obtener_valor(root, './/cac:AccountingCustomerParty//cbc:CompanyID'),
                        "Email_Proveedor": obtener_valor(root, './/cac:AccountingSupplierParty//cac:Party//cac:Contact//cbc:ElectronicMail'),
                        "Telefono": obtener_telefono(root),
                        "Descripcion": " - ".join(descripciones) if descripciones else "Sin descripción",
                        "Base_Imp": float(obtener_valor(root, './/cac:LegalMonetaryTotal/cbc:LineExtensionAmount')),
                        "IVA": float(obtener_valor(root, './/cac:TaxTotal/cbc:TaxAmount')),
                        "Total": float(obtener_valor(root, './/cac:LegalMonetaryTotal/cbc:PayableAmount'))
                    }
                    data_facturas.append(item)
    
    df = pd.DataFrame(data_facturas)
    
    # Visualización completa sin recortes
    st.dataframe(df, use_container_width=True)
    
    # Botón de descarga
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    st.download_button("Descargar Reporte Completo", data=output.getvalue(), file_name="Reporte_Contable_Final.xlsx")
