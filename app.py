import streamlit as st
import pandas as pd
import zipfile
import io
from lxml import etree

# 1. CONFIGURACIÓN DE APARIENCIA DARK MODE
st.set_page_config(page_title="Ortiz y Asociados | Portal Contable", layout="wide")

st.markdown("""
    <style>
    :root { --bg-color: #0e1117; --text-color: #ffffff; }
    .main { background-color: var(--bg-color); color: var(--text-color); }
    .empresa-header { color: #00ffa3; text-align: center; font-weight: 700; font-size: 3rem; margin-bottom: 5px; }
    .subtitle-header { color: #cccccc; text-align: center; font-weight: 300; font-size: 1.2rem; margin-bottom: 40px; }
    </style>
""", unsafe_allow_html=True)

# 2. ENCABEZADO
st.markdown('<div class="empresa-header">🏛️ Ortiz y Asociados</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle-header">Procesador Inteligente de Facturas Electrónicas XML</div>', unsafe_allow_html=True)

# 3. INTERFAZ DE CARGA
uploaded_files = st.file_uploader("📥 Arrastre o seleccione sus archivos ZIP aquí:", type=["zip"], accept_multiple_files=True)

if uploaded_files:
    data = []
    with st.spinner('Procesando facturas con lógica quirúrgica...'):
        for uploaded_file in uploaded_files:
            with zipfile.ZipFile(uploaded_file, 'r') as z:
                for file_name in z.namelist():
                    if file_name.endswith(".xml"):
                        try:
                            content = z.read(file_name)
                            parser = etree.XMLParser(recover=True)
                            root = etree.fromstring(content, parser)
                            
                            # Lógica Quirúrgica (Resumen Raíz)
                            tax_totals = root.xpath('./*[local-name()="TaxTotal"]')
                            base_gravada, total_iva, otros_impuestos = 0.0, 0.0, 0.0
                            
                            for tax in tax_totals:
                                for sub in tax.xpath('./*[local-name()="TaxSubtotal"]'):
                                    t_id = sub.xpath('.//*[local-name()="TaxScheme"]//*[local-name()="ID"]')
                                    tax_id = t_id[0].text if t_id else ""
                                    amount = float(sub.xpath('./*[local-name()="TaxAmount"]')[0].text)
                                    taxable = float(sub.xpath('./*[local-name()="TaxableAmount"]')[0].text) if sub.xpath('./*[local-name()="TaxableAmount"]') else 0.0
                                    
                                    if tax_id == '01':
                                        total_iva += amount
                                        base_gravada += taxable
                                    else:
                                        otros_impuestos += amount

                            total_factura = float(root.xpath('.//*[local-name()="PayableAmount"]')[0].text)
                            
                            data.append({
                                "ID Factura": root.xpath('.//*[local-name()="ID"]')[0].text,
                                "Proveedor": root.xpath('.//*[local-name()="AccountingSupplierParty"]//*[local-name()="RegistrationName"]')[0].text,
                                "Base Gravada": round(base_gravada, 2),
                                "Total IVA": round(total_iva, 2),
                                "Otros Impuestos": round(otros_impuestos, 2),
                                "Total Factura": round(total_factura, 2)
                            })
                        except Exception as e:
                            st.error(f"Error en {file_name}")

    if data:
        df = pd.DataFrame(data)
        # Totalización
        totales = df[['Base Gravada', 'Total IVA', 'Otros Impuestos', 'Total Factura']].sum()
        df_final = pd.concat([df, pd.DataFrame([totales.rename(index=str).to_dict()])], ignore_index=True)
        df_final.loc[df_final.index[-1], 'ID Factura'] = 'TOTAL GENERAL'

        st.subheader("📊 Resultados del Procesamiento")
        st.dataframe(df_final, use_container_width=True)

        # Descarga
        output = io.BytesIO()
        df_final.to_excel(output, index=False)
        st.download_button("🚀 Descargar Reporte Final (Excel)", data=output.getvalue(), file_name="Reporte_Ortiz_Asociados.xlsx")
