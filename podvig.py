import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import LocateControl
import psycopg2
from psycopg2 import sql
import os
import streamlit.components.v1 as components
import time

st.set_page_config(
    page_title="Подвиги",
    layout="centered",  # "wide" или "centered"
    initial_sidebar_state="expanded",  # "auto", "expanded", "collapsed"
)

# Конфигурация подключения к БД
DB_CONFIG = {
    "dbname": "dimas",
    "user": "postgres",
    "password": "Ilichev71",
    "host": "147.45.146.171",
    "port": "5432"
}

# Получение информации о конкретном подвиге
def get_act_details(act_title):
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT a.act_id, a.title, a.description, a.participants, a.act_date, a.latitude, a.longitude, i.video_path, i.image_path
                    FROM Acts a
                    LEFT JOIN Images i ON a.act_id = i.act_id
                    WHERE a.title = %s
                """, (act_title,))
                result = cursor.fetchone()
                if result:
                    return dict(zip(
                        ["act_id", "title", "description", "participants", "act_date", "latitude", "longitude", "video_path", "image_path"],
                        result
                    ))
    except Exception as e:
        st.error(f"Ошибка при загрузке данных: {e}")
    return None

# Получение всех подвигов из БД
def get_acts():
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT act_id, title, act_date, latitude, longitude
                    FROM Acts
                """)
                return [
                    dict(zip([desc[0] for desc in cursor.description], row))
                    for row in cursor.fetchall()
                ]
    except Exception as e:
        st.error(f"Ошибка при загрузке данных: {e}")
        return []

def show_act_details(act_title):
    details = get_act_details(act_title)
    if not details:
        st.error("Подвиг не найден")
        return

    coords = f"{details['latitude']}, {details['longitude']}"
    img_path = os.path.join("img", details['image_path']) if details['image_path'] else None
    gif_path = os.path.join("gif", details['video_path']) if details['video_path'] else None

    # Сброс при смене подвига
    if 'last_shown_act' not in st.session_state or st.session_state.last_shown_act != act_title:
        st.session_state['show_gif'] = False
        st.session_state['last_shown_act'] = act_title

    st.markdown("""
        <style>
            .info-container {
                font-size: 18px;
                font-family: 'Segoe UI', sans-serif;
                line-height: 1.7;
                margin-top: 20px;
                padding: 20px;
                background: #f9f9f9;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }
        </style>
    """, unsafe_allow_html=True)

    with st.expander(f"**📌 {details['title']}**", expanded=True):
        st.write(f"**📅 Дата:** {details['act_date']}")
        st.write(f"**👥 Участники:** {details['participants']}")
        st.write(f"**📍 Координаты:** {details['latitude']}, {details['longitude']}")
        st.write(f"**📝 Описание:** {details['description']}")

    # Отображение фото или gif
    if not st.session_state.get('show_gif', False):
        if img_path and os.path.exists(img_path):
            st.image(img_path, use_container_width=True)
        else:
            st.warning("Изображение не найдено.")
        if gif_path and os.path.exists(gif_path):

            if st.button("Анимировать"):
                st.session_state['show_gif'] = True
    else:
        if gif_path and os.path.exists(gif_path):
            with open(gif_path, "rb") as f:
                gif_bytes = f.read()
                st.image(gif_bytes, use_container_width=True)

            if st.button("Стоп"):
                st.session_state['show_gif'] = False

        else:
            st.warning("GIF-файл не найден.")

# Отображение карты с подвигами
def show_map():
    st.title("🗺️ Подвиги")
    st.markdown("Кликните на маркер, чтобы увидеть подробности")

    acts_data = get_acts()
    m = folium.Map(location=[55.75, 37.61], zoom_start=5)

    m.get_root().html.add_child(folium.Element("""
        <style>
        .leaflet-control-attribution { display: none !important; }
        </style>
    """))

    LocateControl(auto_start=False).add_to(m)

    for act in acts_data:
        popup_html = f"""
        <div style='font-family:Arial; font-size:14px;'>
            <strong>{act['title']}</strong><br>
            <small>{act['act_date']}</small>
        </div>
        """
        popup = folium.Popup(popup_html, max_width=250)
        folium.Marker(
            location=[act["latitude"], act["longitude"]],
            popup=popup,
            tooltip=act["title"],
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(m)

    map_data = st_folium(m, use_container_width=True, height=500)

    if 'selected_act' not in st.session_state:
        st.session_state.selected_act = None

    if map_data.get('last_object_clicked_tooltip'):
        st.session_state.selected_act = map_data['last_object_clicked_tooltip']
        st.markdown("""
        <script>
        setTimeout(() => {
            const el = document.getElementById('details');
            if (el) el.scrollIntoView({ behavior: 'smooth' });
        }, 100);
        </script>
        """, unsafe_allow_html=True)

    if st.session_state.selected_act:
        show_act_details(st.session_state.selected_act)

# Запуск приложения
if __name__ == "__main__":
    show_map()
