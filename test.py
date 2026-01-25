import streamlit as st
import pandas as pd
from io import BytesIO

# ============================================================
# 🔐 AUTHENTIFICATION
# ============================================================
if "login" not in st.session_state:
    st.session_state["login"] = False

def login(username, password):
    users = {
        "aurore": {"password": "12345", "name": "Aurore Demoulin"},
        "laure.froidefond": {"password": "Laure2019$", "name": "Laure Froidefond"},
        "Bruno": {"password": "Toto1963$", "name": "Toto El Gringo"},
        "Manana": {"password": "193827", "name": "Manana"}
    }
    if username in users and password == users[username]["password"]:
        st.session_state["login"] = True
        st.session_state["name"] = users[username]["name"]
        st.rerun()
    else:
        st.error("❌ Identifiants incorrects")

if not st.session_state["login"]:
    st.set_page_config(page_title="Connexion", layout="centered")
    st.title("🔑 Connexion espace expert-comptable")
    username = st.text_input("Identifiant")
    password = st.text_input("Mot de passe", type="password")
    if st.button("Connexion"):
        login(username, password)
    st.stop()

# ============================================================
# 🎯 PAGE PRINCIPALE
# ============================================================
st.set_page_config(page_title="Générateur écritures ventes", page_icon="📘", layout="centered")
st.title("📘 Générateur d'écritures comptables – Ventes")
st.caption(f"Connecté en tant que **{st.session_state['name']}**")

uploaded_file = st.file_uploader("📂 Fichier Excel Factura", type=["xls", "xlsx"])

# ============================================================
# 🧠 FONCTIONS
# ============================================================
def clean_amount(x):
    if pd.isna(x):
        return 0.0
    return float(str(x).replace("€", "").replace("%", "").replace(" ", "").replace(",", "."))

def compte_client(nom):
    nom = str(nom).strip().upper()
    lettre = nom[0] if nom and nom[0].isalpha() else "X"
    return f"4110{lettre}0000"

def compte_vente_mono(taux):
    return {
        5.5: "704000000",
        10.0: "704100000",
        20.0: "704200000",
        0.0: "704500000"
    }.get(taux, "704300000")

# ============================================================
# 🚀 TRAITEMENT
# ============================================================
if uploaded_file:
    df = pd.read_excel(uploaded_file, dtype=str)
    df.columns = df.columns.str.strip()

    df = df[[
        "N° Facture",
        "Date",
        "Nom Facture",
        "Total HT",
        "Total HT d'origine sur quantité unitaire",
        "Taux de tva"
    ]]

    df.columns = ["Facture", "Date", "Client", "HT_FACTURE", "HT_LIGNE", "Taux"]

    df["HT_FACTURE"] = df["HT_FACTURE"].apply(clean_amount)
    df["HT_LIGNE"] = df["HT_LIGNE"].apply(clean_amount)
    df["Taux"] = df["Taux"].apply(clean_amount)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d/%m/%Y")

    ecritures = []

    for facture, g in df.groupby("Facture"):
        date = g["Date"].iloc[0]
        client = g["Client"].iloc[0]
        ht_facture = g["HT_FACTURE"].max()
        libelle = f"Facture {facture} - {client}"
        compte_cli = compte_client(client)

        ventilation = (
            g.groupby("Taux")["HT_LIGNE"]
            .sum()
            .reset_index()
        )

        ventilation = ventilation[ventilation["HT_LIGNE"] != 0]

        # ======================
        # REQUALIFICATION MONO TVA
        # ======================
        if len(ventilation) == 1:
            taux = ventilation.iloc[0]["Taux"]
            tva = round(ht_facture * taux / 100, 2)
            ttc = round(ht_facture + tva, 2)

            ecritures += [
                {"Date": date, "Journal": "VT", "Numéro de compte": compte_cli,
                 "Numéro de pièce": facture, "Libellé": libelle,
                 "Débit": ttc, "Crédit": ""},
                {"Date": date, "Journal": "VT",
                 "Numéro de compte": compte_vente_mono(taux),
                 "Numéro de pièce": facture, "Libellé": libelle,
                 "Débit": "", "Crédit": ht_facture},
                {"Date": date, "Journal": "VT",
                 "Numéro de compte": "445740000",
                 "Numéro de pièce": facture, "Libellé": libelle,
                 "Débit": "", "Crédit": tva}
            ]

        # ======================
        # VRAIE MULTI TVA
        # ======================
        else:
            tva_totale = 0

            for _, row in ventilation.iterrows():
                tva_ligne = round(row["HT_LIGNE"] * row["Taux"] / 100, 2)
                tva_totale += tva_ligne

                ecritures.append({
                    "Date": date, "Journal": "VT",
                    "Numéro de compte": "445740000",
                    "Numéro de pièce": facture,
                    "Libellé": f"{libelle} TVA {row['Taux']}%",
                    "Débit": "", "Crédit": tva_ligne
                })

            ttc = round(ht_facture + tva_totale, 2)

            ecritures += [
                {"Date": date, "Journal": "VT", "Numéro de compte": compte_cli,
                 "Numéro de pièce": facture, "Libellé": libelle,
                 "Débit": ttc, "Crédit": ""},
                {"Date": date, "Journal": "VT",
                 "Numéro de compte": "704300000",
                 "Numéro de pièce": facture, "Libellé": libelle,
                 "Débit": "", "Crédit": ht_facture}
            ]

    df_out = pd.DataFrame(ecritures)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_out.to_excel(writer, index=False, sheet_name="Écritures")
    output.seek(0)

    st.download_button(
        "📥 Télécharger les écritures comptables",
        data=output,
        file_name="ecritures_ventes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
