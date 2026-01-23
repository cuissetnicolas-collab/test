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

def compte_vente(taux):
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

    df = df[["N° Facture", "Date", "Nom Facture", "Total HT", "Taux de tva"]]
    df.columns = ["Facture", "Date", "Client", "HT", "Taux"]

    df["HT"] = df["HT"].apply(clean_amount)
    df["Taux"] = df["Taux"].apply(clean_amount)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d/%m/%Y")

    ecritures = []

    # ========================================================
    # 🔁 TRAITEMENT PAR FACTURE
    # ========================================================
    for facture, bloc in df.groupby("Facture"):

        date = bloc["Date"].iloc[0]
        client = bloc["Client"].iloc[0]
        compte_cli = compte_client(client)
        libelle = f"Facture {facture} - {client}"

        # --- Calculs globaux facture ---
        bloc["TVA"] = (bloc["HT"] * bloc["Taux"] / 100).round(2)
        total_ht = bloc["HT"].sum()
        total_tva = bloc["TVA"].sum()
        total_ttc = total_ht + total_tva

        # ✅ LIGNE CLIENT UNIQUE
        ecritures.append({
            "Date": date,
            "Journal": "VT",
            "Numéro de compte": compte_cli,
            "Numéro de pièce": facture,
            "Libellé": libelle,
            "Débit": round(total_ttc, 2),
            "Crédit": ""
        })

        # --- Ventilation HT + TVA par taux ---
        for taux, sous_bloc in bloc.groupby("Taux"):
            ht = sous_bloc["HT"].sum()
            tva = sous_bloc["TVA"].sum()

            # Vente
            ecritures.append({
                "Date": date,
                "Journal": "VT",
                "Numéro de compte": compte_vente(taux),
                "Numéro de pièce": facture,
                "Libellé": libelle,
                "Débit": "",
                "Crédit": round(ht, 2)
            })

            # TVA
            if abs(tva) > 0.01:
                ecritures.append({
                    "Date": date,
                    "Journal": "VT",
                    "Numéro de compte": "445740000",
                    "Numéro de pièce": facture,
                    "Libellé": libelle,
                    "Débit": "",
                    "Crédit": round(tva, 2)
                })

    df_out = pd.DataFrame(ecritures)

    # ========================================================
    # 📊 CONTRÔLES
    # ========================================================
    total_debit = pd.to_numeric(df_out["Débit"], errors="coerce").sum()
    total_credit = pd.to_numeric(df_out["Crédit"], errors="coerce").sum()

    st.success(f"✅ Écritures générées sans doublon")
    st.info(
        f"Débit : {total_debit:,.2f} € | "
        f"Crédit : {total_credit:,.2f} € | "
        f"Écart : {total_debit - total_credit:,.2f} €"
    )

    st.dataframe(df_out)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_out.to_excel(writer, index=False)
    output.seek(0)

    st.download_button(
        "💾 Télécharger les écritures",
        output,
        "ecritures_ventes.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
