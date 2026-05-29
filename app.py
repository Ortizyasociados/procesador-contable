import streamlit as st
import pandas as pd
import zipfile
import io
from lxml import etree

# 1. CONFIGURACIÓN DE APARIENCIA
st.set_page_config(page_title="Ortiz y Asociados | Portal Contable", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .empresa-header { color: #1a1a1a; text-align: center; font-weight: 600; font-size: 2.5rem; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="empresa-header">🏛️ Ortiz y Asociados | Procesador Inteligente</div>', unsafe_allow_html=True)

uploaded_files = st.file_uploader("Cargue sus archivos ZIP aquí:", type=["zip"], accept_multiple_files=True)

if uploaded_files:
    data = []
    for uploaded_file in uploaded_files:
        with zipfile.ZipFile(uploaded_file, 'r') as z:
            for file_name in z.namelist():
                if file_name.endswith(".xml"):
                    try:
                        # Lectura del XML
                        content = z.read(file_name)
                        parser = etree.XMLParser(recover=True)
                        root = etree.fromstring(content, parser)
                        
                        # --- LÓGICA QUIRÚRGICA: Solo el resumen oficial en la raíz ---
                        # Evitamos los // que causan duplicidad
                        tax_totals = root.xpath('./*[local-name()="TaxTotal"]')
                        
                        base_gravada = 0.0
                        total_iva = 0.0
                        otros_impuestos = 0.0
                        
                        for tax in tax_totals:
                            subtotals = tax.xpath('./*[local-name()="TaxSubtotal"]')
                            for sub in subtotals:
                                tax_type = sub.xpath('.//*[local-name()="TaxScheme"]//*[local-name()="ID"]')
                                tax_id = tax_type[0].text if tax_type else ""
                                tax_amount = float(sub.xpath('./*[local-name()="TaxAmount"]')[0].text)
                                taxable_node = sub.xpath('./*[local-name()="TaxableAmount"]')
                                taxable_amount = float(taxable_node[0].text) if taxable_node else 0.0
                                
                                if tax_id == '01':
                                    total_iva += tax_amount
                                    base_gravada += taxable_amount
                                else:
                                    otros_impuestos += tax_amount

                        # Extracción de totales oficiales
                        total_factura = float(root.xpath('.//*[local-name()="PayableAmount"]')[0].text)
                        base_exenta = max(0.0, total_factura - base_gravada - total_iva - otros_impuestos)
                        
                        data.append({
                            "ID Factura": root.xpath('.//*[local-name()="ID"]')[0].text,
                            "Proveedor": root.xpath('.//*[local-name()="AccountingSupplierParty"]//*[local-name()="RegistrationName"]')[0].text,
                            "Base Gravada": round(base_gravada, 2),
                            "Base Exenta": round(base_exenta, 2),
                            "Total IVA": round(total_iva, 2),
                            "Otros Impuestos": round(otros_impuestos, 2),
                            "Total Factura": round(total_factura, 2)
                        })
                    except Exception as e:
                        st.error(f"Error procesando {file_name}: {e}")

    if data:
        df = pd.DataFrame(data)
        
        # --- TOTALIZAR AL FINAL ---
        totales = df[['Base Gravada', 'Base Exenta', 'Total IVA', 'Otros Impuestos', 'Total Factura']].sum()
        df_final = pd.concat([df, pd.DataFrame([totales.rename(index=str).to_dict()])], ignore_index=True)
        df_final.loc[df_final.index[-1], 'ID Factura'] = 'TOTAL GENERAL'

        st.dataframe(df_final, use_container_width=True)

        # Botón de descarga
        output = io.BytesIO()
        df_final.to_excel(output, index=False)
        st.download_button("📥 Descargar Reporte Final (Excel)", data=output.getvalue(), file_name="Reporte_Contable_Final.xlsx")
