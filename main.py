import requests
import sqlite3
import pandas as pd
import streamlit as st
import xml.etree.ElementTree as ET

# URL do pliku XML
url = "https://firebasestorage.googleapis.com/v0/b/kompreshop.appspot.com/o/xml%2Fkompre.xml?alt=media"

# Pobranie pliku XML
response = requests.get(url)
if response.status_code == 200:
    xml_data = response.content
else:
    print(f"Błąd podczas pobierania pliku: {response.status_code}")
    exit()

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
        "name": item.find("name").text,
        "category": item.find("cat").text,
        "ram": attrs.get("Ilość pamięci RAM"),
        "screen_size": attrs.get("Przekątna ekranu"),
        "resolution": attrs.get("Rozdzielczość ekranu"),
        "processor_series": attrs.get("Seria procesora"),
        "processor": attrs.get("Procesor"),
        "touchscreen": attrs.get("Ekran dotykowy"),
        "cores": attrs.get("Ilość rdzeni"),
    }
    data.append(record)

# Konwersja danych do DataFrame
df = pd.DataFrame(data)

# Zapisanie danych do SQLite
conn = sqlite3.connect("produkty.db")
df.to_sql("produkty", conn, if_exists="replace", index=False)
conn.close()

print("Dane zostały zapisane w bazie danych SQLite jako tabela 'produkty'.")

# Streamlit - interaktywna aplikacja
# Połączenie z bazą SQLite
conn = sqlite3.connect("produkty.db")

# Wczytanie danych z bazy (na potrzeby dynamicznych wartości filtrów)
df = pd.read_sql_query("SELECT * FROM produkty", conn)

# Tytuł aplikacji
st.title("Interaktywne filtrowanie produktów")

# Filtry
# 1. Filtr po cenie
min_price = st.slider("Minimalna cena", int(df['price'].min()), int(df['price'].max()), int(df['price'].min()))
max_price = st.slider("Maksymalna cena", int(df['price'].min()), int(df['price'].max()), int(df['price'].max()))

# 2. Filtr po dostępności na stanie
stock_filter = st.checkbox("Pokaż tylko produkty dostępne na stanie (stock > 0)")

# 3. Filtr po kategorii
category = st.selectbox("Wybierz kategorię", options=["Wszystkie"] + df['category'].unique().tolist())

# 4. Filtr po nazwie produktu
product_name = st.text_input("Szukaj produktu (fragment nazwy):", "")

# 5. Filtr po pamięci RAM
ram = st.selectbox("Wybierz pamięć RAM", options=["Wszystkie"] + df['ram'].dropna().unique().tolist())

# 6. Filtr po wielkości ekranu
screen_size = st.selectbox("Wybierz wielkość ekranu", options=["Wszystkie"] + df['screen_size'].dropna().unique().tolist())

# 7. Filtr po rozdzielczości
resolution = st.selectbox("Wybierz rozdzielczość ekranu", options=["Wszystkie"] + df['resolution'].dropna().unique().tolist())

# 8. Filtr po serii procesora
processor_series = st.selectbox("Wybierz serię procesora", options=["Wszystkie"] + df['processor_series'].dropna().unique().tolist())

# 9. Filtr po procesorze
processor = st.selectbox("Wybierz procesor", options=["Wszystkie"] + df['processor'].dropna().unique().tolist())

# 10. Filtr po ekranie dotykowym
touchscreen = st.selectbox("Ekran dotykowy", options=["Wszystkie", "Tak", "Nie"])

# 11. Filtr po liczbie rdzeni
cores = st.selectbox("Wybierz liczbę rdzeni", options=["Wszystkie"] + df['cores'].dropna().unique().tolist())

# Budowanie zapytania SQL na podstawie filtrów
query = f"""
SELECT * FROM produkty
WHERE price BETWEEN {min_price} AND {max_price}
"""
if stock_filter:
    query += " AND stock > 0"
if category != "Wszystkie":
    query += f" AND category = '{category}'"
if product_name:
    query += f" AND name LIKE '%{product_name}%'"
if ram != "Wszystkie":
    query += f" AND ram = '{ram}'"
if screen_size != "Wszystkie":
    query += f" AND screen_size = '{screen_size}'"
if resolution != "Wszystkie":
    query += f" AND resolution = '{resolution}'"
if processor_series != "Wszystkie":
    query += f" AND processor_series = '{processor_series}'"
if processor != "Wszystkie":
    query += f" AND processor = '{processor}'"
if touchscreen != "Wszystkie":
    query += f" AND touchscreen = '{touchscreen}'"
if cores != "Wszystkie":
    query += f" AND cores = '{cores}'"

# Pobranie danych po zastosowaniu filtrów
filtered_data = pd.read_sql_query(query, conn)

# Wyświetlanie wyników
st.subheader("Wyniki filtrowania:")
st.dataframe(filtered_data)

# Eksport do Excela
if st.button("Eksportuj do Excela"):
    filtered_data.to_excel("filtrowane_produkty.xlsx", index=False)
    st.success("Plik został zapisany jako 'filtrowane_produkty.xlsx'")

# Zamknięcie połączenia z bazą
conn.close()
