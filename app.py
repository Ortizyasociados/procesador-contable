import streamlit as st
import pandas as pd
import zipfile
import io
import xml.etree.ElementTree as ET

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
                    
                    # Lógica para fechas y tipo de pago
                    fecha_vencimiento = obtener_valor(root, './/cbc:DueDate')
                    if fecha_vencimiento == "0":
                        fecha_vencimiento = obtener_valor(root, './/cbc:PaymentDueDate')
                    tipo_pago = "CRÉDITO" if (fecha_vencimiento != "0" and fecha_vencimiento != fecha_emision) else "CONTADO"

                    if numero != "0" and root.find('.//cac:InvoiceLine', ns) is not None:
                        if numero in numeros_procesados:
                            data_avisos.append({"Tipo_Alerta": "Duplicado", "Archivo": nombre_xml, "Mensaje": f"Duplicado: {numero}"})
                        else:
                            descripciones = [d.text for d in root.findall('.//cac:InvoiceLine/cac:Item/cbc:Description', ns) if d.text]
                            
                            # Diccionario con las columnas tal cual las pediste
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
                            numeros_procesados.add(numero)
                    else:
                        data_avisos.append({"Tipo_Alerta": "Revisión", "Archivo": nombre_xml, "Mensaje": "Revisar estructura"})

    df = pd.DataFrame(data_facturas)
    st.dataframe(df, use_container_width=True)
    
    # Totales en pantalla
    if not df.empty:
        col1, col2 = st.columns(2)
        col1.metric("Total Base Imponible", f"{df['Base_Imp'].sum():,.2f}")
        col2.metric("Total IVA", f"{df['IVA'].sum():,.2f}")
    
    if data_avisos:
        st.subheader("Archivos para revisión manual")
        st.dataframe(pd.DataFrame(data_avisos), use_container_width=True)

    # Excel con totales escritos en las celdas
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte')
        worksheet = writer.sheets['Reporte']
        
        # Escribir totales abajo
        if not df.empty:
            totales_fila = len(df) + 1
            worksheet.write(totales_fila, 0, "Total")
            worksheet.write(totales_fila, 12, df['Base_Imp'].sum())
            worksheet.write(totales_fila, 13, df['IVA'].sum())
            worksheet.write(totales_fila, 14, df['Total'].sum())
        
        # Escribir Avisos
        if data_avisos:
            fila_avisos = len(df) + 4
            pd.DataFrame(data_avisos).to_excel(writer, index=False, sheet_name='Reporte', startrow=fila_avisos)
            worksheet.write(fila_avisos - 1, 0, "ARCHIVOS PARA REVISIÓN MANUAL")
            
    st.download_button("Descargar Excel Final", data=output.getvalue(), file_name="Reporte_Contable_Final.xlsx")
