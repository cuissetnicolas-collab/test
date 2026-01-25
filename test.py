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

if st.button("🔓 Déconnexion"):
    st.session_state["login"] = False
    st.rerun()

uploaded_file = st.file_uploader("📂 Fichier Excel Factura", type=["xls", "xlsx"])

# ============================================================
# 🧠 FONCTIONS UTILITAIRES
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
# 🚀 TRAITEMENT DU FICHIER
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
        compte_cli = compte_client(client)
        libelle = f"Facture {facture} - {client}"

        # 🔎 TAUX NON NULS UNIQUES
        taux_reels = sorted(t for t in g["Taux"].unique() if t != 0)

        # ====================================================
        # MONO TVA
        # ====================================================
        if len(taux_reels) <= 1:
            taux = taux_reels[0] if taux_reels else 0.0
            tva = round(ht_facture * taux / 100, 2)
            ttc = round(ht_facture + tva, 2)

            ecritures += [
                {"Date": date, "Journal": "VT", "Numéro de compte": compte_cli,
                 "Numéro de pièce": facture, "Libellé": libelle,
                 "Débit": ttc, "Crédit": ""},

                {"Date": date, "Journal": "VT",
                 "Numéro de compte": compte_vente_mono(taux),
                 "Numéro de pièce": facture, "Libellé": libelle,
                 "Débit": "", "Crédit": ht_facture}
            ]

            if tva != 0:
                ecritures.append({
                    "Date": date, "Journal": "VT",
                    "Numéro de compte": "445740000",
                    "Numéro de pièce": facture, "Libellé": libelle,
                    "Débit": "", "Crédit": tva
                })

        # ====================================================
        # MULTI TVA
        # ====================================================
        else:
            tva_totale = 0.0

            for taux in taux_reels:
                ht_taux = g.loc[g["Taux"] == taux, "HT_LIGNE"].sum()
                tva_taux = round(ht_taux * taux / 100, 2)
                tva_totale += tva_taux

                if tva_taux != 0:
                    ecritures.append({
                        "Date": date, "Journal": "VT",
                        "Numéro de compte": "445740000",
                        "Numéro de pièce": facture,
                        "Libellé": f"{libelle} TVA {taux}%",
                        "Débit": "", "Crédit": tva_taux
                    })

            ttc = round(ht_facture + tva_totale, 2)

            ecritures += [
                {"Date": date, "Journal": "VT",
                 "Numéro de compte": compte_cli,
                 "Numéro de pièce": facture, "Libellé": libelle,
                 "Débit": ttc, "Crédit": ""},

                {"Date": date, "Journal": "VT",
                 "Numéro de compte": "704300000",
                 "Numéro de pièce": facture, "Libellé": libelle,
                 "Débit": "", "Crédit": ht_facture}
            ]

    # ============================================================
    # 📊 SORTIE & EXPORT
    # ============================================================
    df_out = pd.DataFrame(ecritures)

    st.success(f"✅ {df_out['Numéro de pièce'].nunique()} factures générées")
    st.dataframe(df_out.head(30))

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_out.to_excel(writer, index=False, sheet_name="Ecritures")
    buffer.seek(0)

    st.download_button(
        "📥 Télécharger les écritures Excel",
        data=buffer,
        file_name="ecritures_ventes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("⬆️ Charge un fichier Excel Factura pour commencer")
