import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO
from zipfile import ZipFile
import datetime as dt
import csv

@st.cache_data
def leer_archivo(f):
    d = pd.read_csv(f,dtype=str)
    d = d.rename(columns={'POSICIÓN':'POSICION'})
    if 'preg1' in d.columns:
        d['PROCESO'] = 'Evaluación de Potencial'
        d = d.rename(columns= lambda x: x.replace('preg','item') if x.startswith('preg') else x)
    return d

@st.cache_data
def resumen(df):
    maxItems = {
        'ESTUDIOS GENERALES CIENCIAS': 76,
        'ESTUDIOS GENERALES LETRAS': 68,
        'ARQUITECTURA Y URBANISMO': 58,
        'EDUCACION' : 76,
        'ARTE Y DISEÑO': 68,
        'ARTES ESCÉNICAS': 68,
        'GASTRONOMÍA, HOTELERÍA Y TURISMO': 68,
    }
    st.write(f'**Número de registros leídos**: {df.shape[0]}')
    items = df.filter(regex='item.*').columns
    st.write(f'**Primer ítem**: {items[0]}')
    st.write(f'**Último ítem**: {items[-1]}')
    df['MAXITEMS'] = df['UNIDAD'].apply(lambda x: maxItems[x] if x in maxItems else 76)
    df['MAXITEMS'] = np.where(df['PROCESO']=='Evaluación de Potencial', 96, df['MAXITEMS'])
    marcas = df.apply(
        lambda x: x['item1':f'item{x["MAXITEMS"]}'].fillna(' '),axis=1
    ).reindex(items,axis=1)
    errores = marcas.apply(lambda x:x.str.startswith('!!ERROR!!')).sum(axis=1)
    blancos = (marcas == ' ').sum(axis=1)
    dobles = (marcas.apply(lambda x:x.str.len()) > 1).sum(axis=1) - errores
    res = df[['EXAMEN','AULA','POSICION']].join(
        blancos.rename('BLANCOS')
    ).join(
        errores.rename('ERRORES')
    ).join(
        dobles.rename('DOBLES')
    )
    res['TOTAL'] = res.loc[:,'BLANCOS':].sum(axis=1)
    return res.sort_values('TOTAL',ascending=False)

def zip_archivos(df,lectura):
    if 'SEDE' not in df.columns:
        df['SEDE'] = 'Lima'
    sede = df['SEDE'].unique()[0]
    fecha = dt.datetime.now().strftime(r'%Y-%m-%d %H:%M:%S')
    tempZip = BytesIO()
    with ZipFile(tempZip,'w') as zf:
        with zf.open(f'{sede} - {fecha}.csv','w') as procesoBuffer:
            procesoBuffer.write(lectura.getvalue())
        for proceso in df['PROCESO'].unique():
            with zf.open(f'{sede} - {proceso} - {fecha}.csv','w') as procesoBuffer:
                df[df['PROCESO']==proceso].drop(columns='PROCESO').to_csv(procesoBuffer,index=False,quoting=csv.QUOTE_ALL)
    st.download_button("Descargar archivos",data=tempZip.getvalue(),file_name=f'{sede} - {fecha}.zip',mime="application/zip")
    tempZip.close()


def main():
    st.title('Verificar archivos de lectura')
    lectura = st.file_uploader('Archivo de lectura')
    if lectura:
        df = leer_archivo(lectura)
        res = resumen(df)
        zip_archivos(df,lectura)
        st.header('Revisión de fichas')
        t = st.slider('Número de incidentes para revisión: ',min_value=0,max_value=96,value=10)
        st.dataframe(res[res['TOTAL']>=t])
        st.header('Fichas por proceso:')
        st.dataframe(df['PROCESO'].value_counts())

if __name__ == '__main__':
    main()