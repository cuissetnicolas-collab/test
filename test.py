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
        "bruno": {"password": "Toto1963$", "name": "Toto El Gringo"},
        "manana": {"password": "193827", "name": "Manana"}
    }
    if username.lower() in users and password == users[username.lower()]["password"]:
        st.session_state["login"] = True
        st.session_state["name"] = users[username.lower()]["name"]
        st.rerun()
    else:
        st.error("❌ Identifiants incorrects")

if not st.session_state["login"]:
    st.set_page_config(page_title="Connexion", layout="centered")
    st.title("🔑 Connexion – Générateur comptable")
    username = st.text_input("Identifiant")
    password = st.text_input("Mot de passe", type="password")
    if st.button("Connexion"):
        login(username, password)
    st.stop()

# ============================================================
# 🎯 INTERFACE
# ============================================================
st.set_page_config(page_title="Écritures de ventes", page_icon="📘", layout="centered")
st.title("📘 Générateur d'écritures comptables – Ventes")
st.caption(f"Connecté en tant que **{st.session_state['name']}**")

if st.button("🔓 Déconnexion"):
    st.session_state["login"] = False
    st.rerun()

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
        taux_uniques = g["Taux"].unique()
        compte_cli = compte_client(client)
        libelle = f"Facture {facture} - {client}"

        # ====================================================
        # MONO TVA
        # ====================================================
        if len(taux_uniques) == 1:
            taux = taux_uniques[0]
            tva = round(ht_facture * taux / 100, 2)
            ttc = round(ht_facture + tva, 2)

            ecritures.extend([
                {"Date": date, "Journal": "VT", "Numéro de compte": compte_cli,
                 "Numéro de pièce": facture, "Libellé": libelle, "Débit": ttc, "Crédit": ""},
                {"Date": date, "Journal": "VT", "Numéro de compte": compte_vente_mono(taux),
                 "Numéro de pièce": facture, "Libellé": libelle, "Débit": "", "Crédit": ht_facture}
            ])

            if tva != 0:
                ecritures.append({
                    "Date": date, "Journal": "VT", "Numéro de compte": "445710000",
                    "Numéro de pièce": facture, "Libellé": libelle,
                    "Débit": "", "Crédit": tva
                })

        # ====================================================
        # MULTI TVA (SÉCURISÉ)
        # ====================================================
        else:
            tva_totale = 0

            lignes_valides = g[g["HT_LIGNE"] != 0]

            for taux, sous_groupe in lignes_valides.groupby("Taux"):
                ht_taux = sous_groupe["HT_LIGNE"].sum()
                tva = round(ht_taux * taux / 100, 2)
                tva_totale += tva

                if tva != 0:
                    ecritures.append({
                        "Date": date,
                        "Journal": "VT",
                        "Numéro de compte": "445710000",
                        "Numéro de pièce": facture,
                        "Libellé": f"{libelle} TVA {taux}%",
                        "Débit": "",
                        "Crédit": tva
                    })

            ttc = round(ht_facture + tva_totale, 2)

            ecritures.extend([
                {"Date": date, "Journal": "VT", "Numéro de compte": compte_cli,
                 "Numéro de pièce": facture, "Libellé": libelle, "Débit": ttc, "Crédit": ""},
                {"Date": date, "Journal": "VT", "Numéro de compte": "704300000",
                 "Numéro de pièce": facture, "Libellé": libelle, "Débit": "", "Crédit": ht_facture}
            ])

    df_out = pd.DataFrame(ecritures)

    st.success(f"✅ {df_out['Numéro de pièce'].nunique()} factures générées")
    st.dataframe(df_out.head(30))

    # ====================================================
    # 📥 TÉLÉCHARGEMENT
    # ====================================================
    buffer = BytesIO()
    df_out.to_csv(buffer, sep=";", index=False, encoding="utf-8-sig")
    buffer.seek(0)

    st.download_button(
        label="📥 Télécharger les écritures comptables",
        data=buffer,
        file_name="ecritures_ventes.csv",
        mime="text/csv"
    )
