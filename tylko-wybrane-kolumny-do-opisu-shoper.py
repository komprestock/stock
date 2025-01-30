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

# Lista wymaganych kolumn
selected_columns = [
    "id", "name", "category", "Ekran dotykowy", "Gwarancja", "Ilość rdzeni", "Informacje dodatkowe",
    "Kamera", "Karta Sieciowa", "Klawiatura", "Kod producenta", "Kondycja", "Kąt widzenia", "Licencja",
    "Model karty graficznej", "Napięcie", "Napęd", "Natężenie", "Obudowa", "Pivot", "Podświetlenie",
    "Pojemność", "Powłoka matrycy", "Procesor", "Producent", "Przekątna ekranu", "Przeznaczenie",
    "Regulacja wysokości", "Rodzaj", "Rodzaj karty graficznej", "SKU", "Seria procesora", "Stan ekranu",
    "Stan obudowy", "Taktowanie", "Transmisja danych", "Typ", "Typ dysku", "Typ licencji", "Typ matrycy",
    "Typ pamięci RAM", "W zestawie", "Wbudowany głośnik", "Zainstalowany system", "Złącza wewnętrzne",
    "Złącza z boku", "Złącza z przodu", "Złącza z tyłu", "Złącza zewnętrzne", "baselinkerID"
]

# Ekstrakcja danych z XML
data = []
for item in root.findall('o'):
    attrs = {attr.get("name"): attr.text for attr in item.find("attrs").findall("a")}
    
    record = {
        "id": item.get("id"),
        "name": item.find("name").text.strip(),
        "category": item.find("cat").text.strip(),
    }
    
    # Dodanie tylko wybranych atrybutów
    for attr in selected_columns:
        record[attr] = attrs.get(attr, "Brak danych").strip() if attrs.get(attr) else "Brak danych"

    data.append(record)

# Konwersja danych do DataFrame
df = pd.DataFrame(data)

# Uzupełnianie brakujących danych w całym DataFrame
df.fillna("Brak danych", inplace=True)

# **Sprawdzanie rzeczywistych kolumn w DataFrame**
existing_columns = [col for col in selected_columns if col in df.columns]
st.write(f"Kolumny zapisane do bazy: {existing_columns}")  # Debugging

# Zapisanie danych do SQLite
conn = sqlite3.connect("produkty.db")
df.to_sql("produkty", conn, if_exists="replace", index=False)
conn.close()

# **Streamlit - interaktywna aplikacja**
# Połączenie z bazą SQLite
conn = sqlite3.connect("produkty.db")

# **Sprawdzenie istniejących kolumn w bazie przed wykonaniem zapytania**
query = "PRAGMA table_info(produkty)"
existing_columns_in_db = pd.read_sql_query(query, conn)["name"].tolist()

# **Dopasowanie listy kolumn do tych, które rzeczywiście istnieją w bazie**
valid_columns = [col for col in selected_columns if col in existing_columns_in_db]

if not valid_columns:
    st.error("Brak wymaganych kolumn w bazie danych!")
    st.stop()

# **Generowanie dynamicznego zapytania SQL**
query = f"SELECT {', '.join(valid_columns)} FROM produkty"
df = pd.read_sql_query(query, conn)

# **Tytuł aplikacji**
st.title("Stan magazynowy kompre.pl (BETA)")

# **Pole do wyszukiwania nazwy produktu**
product_name = st.text_input("Wpisz fragment nazwy produktu:")

# **Filtrowanie kategorii**
category = st.selectbox("Kategoria", options=["Wszystkie"] + df['category'].dropna().unique().tolist())

# **Budowanie zapytania SQL na podstawie aktywnych filtrów**
query = f"SELECT {', '.join(valid_columns)} FROM produkty WHERE 1=1"

if category != "Wszystkie":
    query += f" AND category = '{category}'"

if product_name:
    query += f" AND name LIKE '%{product_name}%'"

# **Pobranie danych po zastosowaniu filtrów**
filtered_data = pd.read_sql_query(query, conn)

# **Wyświetlanie wyników**
st.header("Wyniki filtrowania")
if filtered_data.empty:
    st.warning("Brak wyników dla wybranych filtrów. Spróbuj zmienić ustawienia filtrów.")
else:
    st.write(f"Liczba pozycji: {len(filtered_data)}")
    st.dataframe(filtered_data, use_container_width=True)

    # **Eksport do Excela**
    excel_buffer = io.BytesIO()
    filtered_data.to_excel(excel_buffer, index=False, engine="openpyxl")
    excel_buffer.seek(0)

    st.download_button(
        label="Pobierz dane jako Excel",
        data=excel_buffer,
        file_name="produkty.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
