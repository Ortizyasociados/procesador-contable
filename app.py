import streamlit as st
import pandas as pd
import zipfile
import io
import xml.etree.ElementTree as ET

# Configuración de página con diseño ancho
st.set_page_config(page_title="Ortiz y Asociados | Procesador", layout="wide")

# Estilos personalizados para un look más profesional
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1 { color: #003366; text-align: center; }
    .stApp { border-top: 5px solid #003366; }
    </style>
""", unsafe_allow_html=True)

# Título y Branding
st.title("🏛️ Ortizia Asociados")
st.subheader("Procesador Inteligente de Facturas Electrónicas XML")
st.markdown("---")

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

# Área de subida con diseño mejorado
with st.container():
    st.info("📂 Por favor, cargue los archivos ZIP comprimidos para iniciar el procesamiento contable.")
    uploaded_files = st.file_uploader("", type=["zip"], accept_multiple_files=True)

if uploaded_files:
    data_facturas = []
    data_avisos = []
    numeros_procesados = set()
    
    for uploaded_file in uploaded_files:
        with zipfile.ZipFile(uploaded_file) as z:
            for nombre_xml in z.namelist():
                if nombre_xml.endswith('.xml'):
                    contenido = z.read(nombre_xml).decode('utf-8')
                    if '<Invoice' in contenido:
                        root = ET.fromstring(contenido[contenido.find('<Invoice'):contenido.rfind('</Invoice>')+10])
                    else:
                        root = ET.fromstring(contenido)
                    
                    numero = obtener_valor(root, './/cbc:ID')
                    fecha_emision = obtener_valor(root, './/cbc:IssueDate')
                    fecha_vencimiento = obtener_valor(root, './/cbc:DueDate')
                    if fecha_vencimiento == "0": fecha_vencimiento = obtener_valor(root, './/cbc:PaymentDueDate')
                    tipo_pago = "CRÉDITO" if (fecha_vencimiento != "0" and fecha_vencimiento != fecha_emision) else "CONTADO"

                    if numero != "0" and root.find('.//cac:InvoiceLine', ns) is not None:
                        if numero in numeros_procesados:
                            data_avisos.append({"Tipo_Alerta": "Duplicado", "Archivo": nombre_xml, "Mensaje": f"Duplicado: {numero}"})
                        else:
                            descripciones = [d.text for d in root.findall('.//cac:InvoiceLine/cac:Item/cbc:Description', ns) if d.text]
                            item = {
                                "Item": 0,
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
                            numeros_procesados.add(numero)
                    else:
                        data_avisos.append({"Tipo_Alerta": "Revisión", "Archivo": nombre_xml, "Mensaje": "Revisar estructura"})

    df = pd.DataFrame(data_facturas)
    if not df.empty:
        df['Item'] = range(1, len(df) + 1)
    
    # Visualización organizada en contenedores
    st.markdown("---")
    st.subheader("📊 Resultados del Procesamiento")
    st.dataframe(df, use_container_width=True)
    
    if not df.empty:
        c1, c2 = st.columns(2)
        c1.metric("💰 Total Base Imponible", f"${df['Base_Imp'].sum():,.2f}")
        c2.metric("💳 Total IVA", f"${df['IVA'].sum():,.2f}")
    
    # Avisos siempre visibles si hay algo que revisar
    if data_avisos:
        st.warning("⚠️ Archivos para revisión manual")
        st.dataframe(pd.DataFrame(data_avisos), use_container_width=True)
    
    # Descarga final
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte')
        worksheet = writer.sheets['Reporte']
        if not df.empty:
            totales_fila = len(df) + 1
            worksheet.write(totales_fila, 0, "Total")
            worksheet.write(totales_fila, 13, df['Base_Imp'].sum())
            worksheet.write(totales_fila, 14, df['IVA'].sum())
            worksheet.write(totales_fila, 15, df['Total'].sum())
        if data_avisos:
            fila_avisos = len(df) + 4
            pd.DataFrame(data_avisos).to_excel(writer, index=False, sheet_name='Reporte', startrow=fila_avisos)
            worksheet.write(fila_avisos - 1, 0, "ARCHIVOS PARA REVISIÓN MANUAL")
            
    st.download_button("📥 Descargar Reporte Final (Excel)", data=output.getvalue(), file_name="Reporte_Contable_Final.xlsx")
