from flask import Flask, render_template, request
import folium
import pandas as pd
import requests
import panel as pn

app = Flask(__name__)

# Función para generar el mapa
def generate_map(day, month, year, indicador):
           
    if not day:
        day="01"
    if not month:
        month="01"
    if not year:
        year="1997"
    if not indicador:
        indicador="o3_ug_m3"

    mesStr='0'+str(month)
    diaStr='0'+str(day)
   
    
    # Obtengo los geodatos de las Provincias (delimitación geográfica)
    provincias = requests.get(
        "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/provincias-espanolas/exports/geojson?lang=en&refine=ccaa%3A%22Castilla%20y%20Le%C3%B3n%22&timezone=Europe%2FBerlin"
    ).json()

    url="https://analisis.datosabiertos.jcyl.es/api/explore/v2.1/catalog/datasets/calidad-del-aire-datos-historicos-diarios/exports/csv?limit=-1&refine=fecha%3A%22"+year+"%2F"+mesStr[-2:]+"%2F"+diaStr[-2:]+"%22&timezone=UTC&use_labels=false&epsg=4326"
    # Obtengo los datos en formato csv desde el portal de Datos Abiertos de la Junta de Castilla y León
    calidad_aire = pd.read_csv(
        #"https://analisis.datosabiertos.jcyl.es/api/explore/v2.1/catalog/datasets/calidad-del-aire-datos-historicos-diarios/exports/csv?limit=-1&refine=fecha%3A%222020%22&timezone=UTC&use_labels=false&epsg=4326"
        
        url
    ,sep=";")

    # Elimino registros nullos
    # Pongo a 0 campos nulos o vacios 
    # Sustituyo la provincia Ávila con tilde para que coincidan los dataset
    # Elimino campos que no son necesarios para la representación

    calidad_aire=calidad_aire.fillna(0)
    calidad_aire["provincia"].replace("Avila","Ávila", inplace=True)
    calidad_aire = calidad_aire.drop('estacion', axis = 1)
    calidad_aire = calidad_aire.drop('latitud', axis = 1)
    calidad_aire = calidad_aire.drop('longitud', axis = 1)
    calidad_aire = calidad_aire.drop('posicion', axis = 1)

    # Filtro los datos a visualizar por fecha
    
    DatosDia = calidad_aire.loc[(calidad_aire['fecha'] == year+'-'+mesStr[-2:]+'-'+diaStr[-2:])]
    DatosDia = DatosDia.drop('fecha', axis = 1)
    
    # Agrupo los datos en función de la columna 'provincia'

    DatosDiaAgrupados = DatosDia.groupby('provincia').mean().reset_index()

    # Filtro para el indicador de calidad del aire
   
    match indicador:
        case 'co_mg_m3':                  
                  leyenda="Monóxido de Carbono (mg/m³)"
        case 'no_ug_m3':                  
                  leyenda="Oxido de Nitrógeno (µg/m³)"
        case 'no2_ug_m3':                  
                  leyenda="Dioxido de Nitrógeno (µg/m³)"
        case 'o3_ug_m3':
                  leyenda="Ozono (µg/m³)"
        case 'pm10_ug_m3':
                  leyenda="Partículas < 10 µm (µg/m³)"
        case 'pm25_ug_m3':
                  leyenda="Partículas < 2,5 µm (µg/m³)"
        case 'so2_ug_m3':
                  leyenda="Dióxido de Azufre (µg/m³)"

    # Inicializo el mapa en el centro de Castilla y León

    #m = folium.Map(location=[41.696819, -4.696932], zoom_start=7)
    m = folium.Map(location=[41.997841, -4.694677], zoom_start=7)

    # Dibujo el mapa

    folium.Choropleth(
        geo_data=provincias,
        name="Calidad Aire CYL",
        data=DatosDiaAgrupados,
        columns=["provincia",indicador],
        key_on="properties.provincia",
        fill_color="YlOrRd",    
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name=leyenda,
    ).add_to(m)


    # Iterar sobre las características y añadir el nuevo campo con el valor correspondiente
    for feature in provincias['features']:
        nombre_provincia = feature['properties']['provincia']  # Obtener el nombre de la provincia
        datos_provincia = DatosDiaAgrupados[DatosDiaAgrupados['provincia'] == nombre_provincia]
        if not datos_provincia.empty:
            valores = datos_provincia.iloc[0].to_dict()
            feature['properties']['contaminante'] = valores[indicador]


    # Dibujo el tooltip

    style_function = lambda x: {'fillColor': '#ffffff',
                                'color':'#000000',
                                'fillOpacity': 0.1,
                                'weight': 0.1}
    highlight_function = lambda x: {'fillColor': '#000000',
                                    'color':'#000000',
                                    'fillOpacity': 0.50,
                                    'weight': 0.1}
    NIL = folium.features.GeoJson(
        provincias,
        style_function=style_function,
        control=False,
        highlight_function=highlight_function,
        tooltip=folium.features.GeoJsonTooltip(
            fields=['provincia','contaminante'],
            aliases=['Provincia: ',leyenda+": "],
            style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;")
        )
    )
    m.add_child(NIL)
    m.keep_in_front(NIL)
    folium.LayerControl().add_to(m)

      

    # Aquí podrías añadir más capas, marcadores, etc. según tus necesidades y los datos obtenidos
    #m.get_root().width = "960px"
    m.get_root().height = "650px"
    iframe = m.get_root()._repr_html_()

    return iframe
    #return m._repr_html_()
    #return print(url)



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/update_map', methods=['POST'])
def update_map():
    # Obtener la fecha y el indicador seleccionados desde el formulario
    day = request.form['day']
    month = request.form['month']
    year = request.form['year']        
    indicador = request.form['indicator']        
    # Generar el nuevo mapa
    map_html = generate_map(day, month, year, indicador)
    return map_html

if __name__ == '__main__':
    app.run(debug=True)
