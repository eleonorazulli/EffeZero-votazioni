import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import re

# ---------------------------
# GOOGLE AUTH (STREAMLIT CLOUD VERSION)
# ---------------------------

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Usa i Secrets invece di credentials.json
creds_dict = st.secrets["gcp_service_account"]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    creds_dict, scope
)

# Google Sheets
client = gspread.authorize(creds)
sheet = client.open("Votazioni_EffeZero").sheet1

# Google Drive
drive_service = build("drive", "v3", credentials=creds)

# ---------------------------
# APP
# ---------------------------

st.title("📸 Votazioni EffeZero")

contest = st.text_input("Nome del contest")
folder_link = st.text_input("Incolla il link della cartella Google Drive")

def get_folder_id(folder_url):
    match = re.search(r"folders/([a-zA-Z0-9_-]+)", folder_url)
    if match:
        return match.group(1)
    return None

photo_files = []

if folder_link:
    folder_id = get_folder_id(folder_link)

    if folder_id:
        try:
            results = drive_service.files().list(
                q=f"'{folder_id}' in parents and mimeType contains 'image/'",
                fields="files(id, name)",
                pageSize=100
            ).execute()

            photo_files = results.get("files", [])

            if not photo_files:
                st.warning("Nessuna immagine trovata nella cartella.")

        except Exception as e:
            st.error(f"Errore accesso Drive: {e}")
    else:
        st.error("Link cartella non valido.")

st.subheader("Inserisci il tuo nome")
user = st.text_input("Nome")

st.subheader("Seleziona al massimo 3 foto")

selected = []

for i, file in enumerate(photo_files):
    file_id = file["id"]

    try:
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.seek(0)

        st.image(fh, width=400)

        if st.checkbox(f"Vota {file['name']}", key=i):
            selected.append(file_id)

    except Exception as e:
        st.error(f"Errore caricamento immagine: {e}")

if st.button("Invia voto"):
    if contest == "":
        st.warning("Inserisci il nome del contest.")
    elif user == "":
        st.warning("Inserisci il nome prima di inviare.")
    elif len(selected) > 3:
        st.error("Puoi selezionare al massimo 3 foto!")
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for foto in selected:
            sheet.append_row([contest, user, foto, timestamp])

        st.success("Voto salvato correttamente!")

# ---------------------------
# CLASSIFICA
# ---------------------------

st.subheader("🏆 Classifica attuale")

data = sheet.get_all_records()
df = pd.DataFrame(data)

if not df.empty and contest:
    df_contest = df[df["Contest"] == contest]

    if not df_contest.empty:
        ranking = df_contest["Foto"].value_counts()
        st.bar_chart(ranking)
    else:
        st.info("Ancora nessun voto per questo contest.")
