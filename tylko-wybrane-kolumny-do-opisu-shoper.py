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

# Zestaw wszystkich możliwych atrybutów
all_attributes = set()

# Pierwsza iteracja - zbieranie nazw atrybutów
for item in root.findall('o'):
    attrs = {attr.get("name") for attr in item.find("attrs").findall("a")}
    all_attributes.update(attrs)

# Konwersja do listy dla późniejszego użycia w DataFrame
all_attributes = sorted(list(all_attributes))

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
    }
    
    # Dodanie wszystkich atrybutów
    for attr in all_attributes:
        record[attr] = attrs.get(attr, "Brak danych").strip() if attrs.get(attr) else "Brak danych"
    
    data.append(record)

# Konwersja danych do DataFrame
df = pd.DataFrame(data)

# Uzupełnianie brakujących danych w całym DataFrame
df.fillna("Brak danych", inplace=True)

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

# Pole do wyszukiwania nazwy produktu
product_name = st.text_input("Wpisz fragment nazwy produktu:")

# Dynamiczne budowanie filtrów
st.header("Filtry")

# Cena
min_price = st.slider("Minimalna cena", int(df['price'].min()), int(df['price'].max()), int(df['price'].min()))
max_price = st.slider("Maksymalna cena", int(df['price'].min()), int(df['price'].max()), int(df['price'].max()))

# Kategoria
category = st.selectbox("Kategoria", options=["Wszystkie"] + df['category'].dropna().unique().tolist())

# Pozostałe atrybuty
filters = {}
for attr in all_attributes:
    unique_values = df[attr].dropna().unique().tolist()
    if unique_values:
        filters[attr] = st.selectbox(f"{attr}", options=["Wszystkie"] + unique_values)

# Budowanie zapytania SQL na podstawie aktywnych filtrów
query = f"SELECT * FROM produkty WHERE price BETWEEN {min_price} AND {max_price}"

if category != "Wszystkie":
    query += f" AND category = '{category}'"

for attr, value in filters.items():
    if value != "Wszystkie":
        query += f" AND `{attr}` = '{value}'"

if product_name:
    query += f" AND name LIKE '%{product_name}%'"

# Pobranie danych po zastosowaniu filtrów
filtered_data = pd.read_sql_query(query, conn)

# Wyświetlanie wyników filtrowania
st.header("Wyniki filtrowania")
if filtered_data.empty:
    st.warning("Brak wyników dla wybranych filtrów. Spróbuj zmienić ustawienia filtrów.")
else:
    # Dodajemy widget umożliwiający wybór kolumn do wyświetlenia i pobrania
    available_columns = list(filtered_data.columns)
    selected_columns = st.multiselect(
        "Wybierz kolumny do wyświetlenia i pobrania", 
        options=available_columns, 
        default=available_columns
    )
    
    if not selected_columns:
        st.error("Wybierz przynajmniej jedną kolumnę.")
    else:
        # Aktualizacja danych do wyświetlenia na podstawie wybranych kolumn
        filtered_data = filtered_data[selected_columns]
        
        st.write(f"Liczba pozycji: {len(filtered_data)}")
        st.dataframe(filtered_data, use_container_width=True)

        # Przygotowanie pliku Excel
        excel_buffer = io.BytesIO()
        filtered_data.to_excel(excel_buffer, index=False, engine="openpyxl")
        excel_buffer.seek(0)

        st.download_button(
            label="Pobierz dane jako Excel",
            data=excel_buffer,
            file_name="produkty.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
