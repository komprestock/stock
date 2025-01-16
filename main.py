import requests
import sqlite3
import pandas as pd
import streamlit as st
import xml.etree.ElementTree as ET
import io

# URL do pliku XML
url = "https://firebasestorage.googleapis.com/v0/b/kompreshop.appspot.com/o/xml%2Fkompre.xml?alt=media"

# Pobranie pliku XML
response = requests.get(url)
if response.status_code == 200:
    xml_data = response.content
else:
    st.error(f"Błąd podczas pobierania pliku: {response.status_code}")
    st.stop()

# Wczytanie XML do struktury drzewa
root = ET.fromstring(xml_data)

# Ekstrakcja danych z XML
data = []
for item in root.findall('o'):
    attrs = {attr.get("name"): attr.text for attr in item.find("attrs").findall("a")}
    record = {
        "id": item.get("id"),
        "url": item.get("url"),
        "price": float(item.get("price")),
        "stock": int(item.get("stock")),
        "name": item.find("name").text.strip(),
        "category": item.find("cat").text.strip(),
        "ram": attrs.get("Ilość pamięci RAM", "").strip(),
        "screen_size": attrs.get("Przekątna ekranu", "").strip(),
        "resolution": attrs.get("Rozdzielczość ekranu", "").strip(),
        "processor_series": attrs.get("Seria procesora", "").strip(),
        "processor": attrs.get("Procesor", "").strip(),
        "touchscreen": attrs.get("Ekran dotykowy", "Nie").strip(),
        "cores": attrs.get("Ilość rdzeni", "").strip(),
        "condition": attrs.get("Kondycja", "").strip(),
        "screen_condition": attrs.get("Stan ekranu", "").strip(),
        "case_condition": attrs.get("Stan obudowy", "").strip(),
    }
    data.append(record)

# Konwersja danych do DataFrame
df = pd.DataFrame(data)

# Zapisanie danych do SQLite
conn = sqlite3.connect("produkty.db")
df.to_sql("produkty", conn, if_exists="replace", index=False)
conn.close()

# Streamlit - interaktywna aplikacja
# Połączenie z bazą SQLite
conn = sqlite3.connect("produkty.db")

# Wczytanie danych z bazy
df = pd.read_sql_query("SELECT * FROM produkty", conn)

# Tytuł aplikacji
st.title("Stan magazynowy kompre.pl (BETA)")

# Filtry w układzie wielu kolumn
st.header("Filtry")
col1, col2, col3, col4 = st.columns(4)

with col1:
    min_price = st.slider("Minimalna cena", int(df['price'].min()), int(df['price'].max()), int(df['price'].min()))
    max_price = st.slider("Maksymalna cena", int(df['price'].min()), int(df['price'].max()), int(df['price'].max()))

with col2:
    stock_filter = st.checkbox("Dostępne (stock > 0)")
    category = st.selectbox("Kategoria", options=["Wszystkie"] + df['category'].dropna().unique().tolist())

with col3:
    screen_size = st.selectbox("Rozmiar ekranu", options=["Wszystkie"] + df['screen_size'].dropna().unique().tolist())
    resolution = st.selectbox("Rozdzielczość", options=["Wszystkie"] + df['resolution'].dropna().unique().tolist())

with col4:
    processor_series = st.selectbox("Seria procesora", options=["Wszystkie"] + df['processor_series'].dropna().unique().tolist())
    processor = st.selectbox("Procesor", options=["Wszystkie"] + df['processor'].dropna().unique().tolist())
    touchscreen = st.selectbox("Ekran dotykowy", options=["Wszystkie", "Tak", "Nie"])
    cores = st.selectbox("Rdzenie", options=["Wszystkie"] + df['cores'].dropna().unique().tolist())

# Pole do wyszukiwania nazwy produktu
product_name = st.text_input("Wpisz fragment nazwy produktu:")

# Budowanie zapytania SQL na podstawie aktywnych filtrów
query = f"SELECT * FROM produkty WHERE price BETWEEN {min_price} AND {max_price}"

if stock_filter:
    query += " AND stock > 0"
if category != "Wszystkie":
    query += f" AND category = '{category}'"
if screen_size != "Wszystkie":
    query += f" AND screen_size = '{screen_size}'"
if resolution != "Wszystkie":
    query += f" AND resolution = '{resolution}'"
if processor_series != "Wszystkie":
    query += f" AND processor_series = '{processor_series}'"
if processor != "Wszystkie":
    query += f" AND processor = '{processor}'"
if touchscreen != "Wszystkie":
    query += f" AND TRIM(touchscreen) = '{touchscreen}'"
if cores != "Wszystkie":
    query += f" AND cores = '{cores}'"
if product_name:
    query += f" AND name LIKE '%{product_name}%'"

# Pobranie danych po zastosowaniu filtrów
filtered_data = pd.read_sql_query(query, conn)

# Wyświetlanie wyników automatycznych
st.header("Wyniki filtrowania")
if filtered_data.empty:
    st.warning("Brak wyników dla wybranych filtrów. Spróbuj zmienić ustawienia filtrów.")
else:
    filtered_data = filtered_data[[
        'id', 'name', 'price', 'stock', 'ram', 'processor_series',
        'cores', 'processor', 'screen_size', 'resolution',
        'touchscreen', 'category', 'condition', 'screen_condition', 'case_condition', 'url'
    ]]
    st.write(f"Liczba pozycji: {len(filtered_data)}")
    st.dataframe(filtered_data, use_container_width=True)

# Sekcja dla polecanych produktów
st.header("Polecane na styczeń i nowe dostawy")
show_recommended = st.checkbox("Pokaż/Ukryj polecane produkty")

# Lista ID polecanych produktów
recommended_ids = ['279877756', '311442840', '238803967', '230090911']  # Wpisz tutaj ID polecanych produktów

if show_recommended:
    recommended_data = df[df['id'].isin(recommended_ids)]
    if not recommended_data.empty:
        st.write(f"Polecane produkty ({len(recommended_data)} pozycji):")
        st.dataframe(recommended_data[[
            'id', 'name', 'price', 'stock', 'ram', 'processor_series',
            'cores', 'processor', 'screen_size', 'resolution',
            'touchscreen', 'category', 'condition', 'screen_condition', 'case_condition', 'url'
        ]], use_container_width=True)
    else:
        st.warning("Brak polecanych produktów do wyświetlenia.")
