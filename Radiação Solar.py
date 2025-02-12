import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import calplot
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static

# Definir a fonte padrão para o matplotlib
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']  # Use 'Arial' ou outra fonte disponível

# Configurações da API do OpenWeatherMap
OWM_API_KEY = '25949bf8f5eb0d3a817da4f3fca399e2'  # Substitua pela sua chave
OWM_BASE_URL = 'http://api.openweathermap.org/data/2.5/weather'

# Configurações da NASA POWER
NASA_POWER_URL = 'https://power.larc.nasa.gov/api/temporal/daily/point'

# Função para obter coordenadas da cidade (OpenWeatherMap)
def get_city_coordinates(city_name):
    params = {
        'q': city_name,
        'appid': OWM_API_KEY,
        'units': 'metric',  # Unidades métricas (Celsius)
        'lang': 'pt_br'     # Idioma português
    }
    response = requests.get(OWM_BASE_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        return data['coord']['lat'], data['coord']['lon']  # Retorna latitude e longitude
    else:
        st.error(f"Erro ao obter coordenadas: {response.status_code}")
        return None, None

# Função para obter dados meteorológicos (OpenWeatherMap)
def get_weather(city_name):
    params = {
        'q': city_name,
        'appid': OWM_API_KEY,
        'units': 'metric',  # Unidades métricas (Celsius)
        'lang': 'pt_br'     # Idioma português
    }
    response = requests.get(OWM_BASE_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Erro ao obter dados: {response.status_code}")
        return None

# Função para obter dados solares (NASA POWER)
def get_solar_data(lat, lon, start_date, end_date):
    params = {
        'parameters': 'ALLSKY_SFC_SW_DWN',  # Irradiação solar global
        'community': 'SB',
        'longitude': lon,
        'latitude': lat,
        'start': start_date.strftime('%Y%m%d'),  # Formatar data para AAAAMMDD
        'end': end_date.strftime('%Y%m%d'),      # Formatar data para AAAAMMDD
        'format': 'JSON'
    }
    response = requests.get(NASA_POWER_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Erro ao obter dados solares: {response.status_code}")
        return None

# Função para processar os dados solares
def process_solar_data(solar_data):
    if not solar_data:
        return None
    
    # Extrair os dados de irradiação solar
    irradiacao_solar = solar_data['properties']['parameter']['ALLSKY_SFC_SW_DWN']
    
    # Converter os dados em um DataFrame
    dados = []
    for data, valor in irradiacao_solar.items():
        if valor != -999:  # Remover valores espúrios
            dados.append({
                'Data': datetime.strptime(data, '%Y%m%d').strftime('%Y-%m-%d'),  # Formatar a data
                'Irradiação Solar (kWh/m²/dia)': valor
            })
    
    df = pd.DataFrame(dados)
    return df

# Função para criar um calendar heatmap
# Função para criar um calendar heatmap
def criar_calendar_heatmap(df_solar):
    # Converter a coluna 'Data' para datetime
    df_solar['Data'] = pd.to_datetime(df_solar['Data'])
    
    # Criar uma série temporal com os dados de irradiação solar
    serie_temporal = df_solar.set_index('Data')['Irradiação Solar (kWh/m²/dia)']
    
    # Ajustar o tamanho da figura
    fig, axs = calplot.calplot(serie_temporal, cmap='YlOrBr', fillcolor='lightgray', linewidth=0.5, figsize=(20, 10))
    
    # Ajustar a posição da barra de cores
    sm = plt.cm.ScalarMappable(cmap='YlOrBr', norm=plt.Normalize(vmin=serie_temporal.min(), vmax=serie_temporal.max()))
    sm.set_array([])  # Necessário para evitar erro
    # plt.colorbar(sm, ax=axs, orientation="horizontal", pad=0.1)

    # Adicionar título ao heatmap
    fig.suptitle("Irradiação Solar Diária (kWh/m²/dia)", y=1.05)  # Ajuste a posição do título
    
    return fig


# Função para exportar os dados em CSV
def export_csv(df):
    return df.to_csv(index=False)

# Função para criar um mapa com Folium
def create_map(latitude, longitude):
    mapa = folium.Map(location=[latitude, longitude], zoom_start=12)
    folium.Marker(
        [latitude, longitude],
        tooltip="Fortaleza",
        popup=f"Fortaleza, Ceará"
    ).add_to(mapa)
    return mapa

# Configuração do tema
st.set_page_config(
    page_title="Dashboard Meteorológico",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://docs.streamlit.io',
        'Report a bug': 'https://github.com/streamlit/streamlit/issues',
        'About': "# Dashboard Meteorológico\nDashboard para monitoramento das condições meteorológicas e irradiação solar."
    }
)

st.title("🌤️ Dashboard Meteorológico e de Energia Renovável")

# Seletor de cidade
city_name = st.text_input("Digite o nome da cidade:", "Fortaleza")

# Obter coordenadas da cidade
lat, lon = get_city_coordinates(city_name)

if lat is not None and lon is not None:
    # Exibir mapa com a localização da cidade
    st.write(f"### Localização de {city_name}")
    mapa = create_map(lat, lon)
    folium_static(mapa)

    # Seletor de datas (período de 6 meses)
    st.write("### Selecione o Período de Análise")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Data de Início", datetime.now() - timedelta(days=180))  # Padrão: 6 meses atrás
    with col2:
        end_date = st.date_input("Data de Fim", datetime.now())  # Padrão: data atual

    # Verificar se as datas são válidas
    if start_date > end_date:
        st.error("A data de início deve ser anterior à data de fim.")
    else:
        # Obter dados solares (NASA POWER)
        solar_data = get_solar_data(lat, lon, start_date, end_date)

        # Obter dados meteorológicos (OpenWeatherMap)
        weather_data = get_weather(city_name)

        # Exibir dados
        if weather_data and solar_data:
            # Dados meteorológicos
            main = weather_data['main']
            weather = weather_data['weather'][0]
            wind = weather_data['wind']
            st.write(f"### Condições atuais em {city_name}")
            col1, col2, col3 = st.columns(3)
            col1.metric("Temperatura", f"{main['temp']}°C")
            col2.metric("Sensação Térmica", f"{main['feels_like']}°C")
            col3.metric("Condição", weather['description'].capitalize())

            col4, col5, col6 = st.columns(3)
            col4.metric("Umidade", f"{main['humidity']}%")
            col5.metric("Velocidade do Vento", f"{wind['speed']} m/s")
            col6.metric("Pressão Atmosférica", f"{main['pressure']} hPa")

            # Processar dados solares
            df_solar = process_solar_data(solar_data)
            if df_solar is not None:
                st.write(f"### Irradiação Solar Global (GHI) de {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}")
                st.write(df_solar)

                # Adicionar a funcionalidade de download
                csv = export_csv(df_solar)
                st.download_button(
                    label="📥 Baixar dados em CSV",
                    data=csv,
                    file_name='dados_solares.csv',
                    mime='text/csv',
                )

                # Gráfico de irradiação solar (área)
                st.write("### Gráfico de Irradiação Solar")
                fig = px.area(
                    df_solar,
                    x='Data',
                    y='Irradiação Solar (kWh/m²/dia)',
                    title="Irradiação Solar ao Longo do Tempo",
                    labels={'Irradiação Solar (kWh/m²/dia)': 'Irradiação Solar (kWh/m²/dia)', 'Data': 'Data'},
                    color_discrete_sequence=['#FFA500']  # Cor laranja para o gráfico
                )
                fig.update_traces(mode="lines+markers", line_shape="spline", fill='tozeroy')  # Linhas suaves e preenchimento
                fig.update_layout(
                    xaxis_title="Data",
                    yaxis_title="Irradiação Solar (kWh/m²/dia)",
                    hovermode="x unified",  # Mostrar informações ao passar o mouse
                    template="plotly_dark"  # Tema escuro para maior impacto visual
                )
                st.plotly_chart(fig)

                # Calendar Heatmap
                st.write("### Calendar Heatmap - Irradiação Solar Diária")
                fig_heatmap = criar_calendar_heatmap(df_solar)
                st.pyplot(fig_heatmap)
