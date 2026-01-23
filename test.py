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
    return float(
        str(x)
        .replace("€", "")
        .replace("%", "")
        .replace(" ", "")
        .replace(",", ".")
    )

def compte_client(nom):
    nom = str(nom).strip().upper()
    lettre = nom[0] if nom and nom[0].isalpha() else "X"
    return f"4110{lettre}0000"

def compte_vente(taux):
    mapping = {
        5.5: "704000000",
        10.0: "704100000",
        20.0: "704200000",
        0.0: "704500000"
    }
    return mapping.get(taux, "704300000")

# ============================================================
# 🚀 TRAITEMENT FICHIER
# ============================================================
if uploaded_file:
    df = pd.read_excel(uploaded_file, dtype=str)
    df.columns = df.columns.str.strip()

    required_cols = [
        "N° Facture",
        "Date",
        "Nom Facture",
        "Total HT",
        "Taux de tva"
    ]

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"❌ Colonnes manquantes : {', '.join(missing)}")
        st.stop()

    df = df[required_cols]
    df.columns = ["Facture", "Date", "Client", "HT", "Taux"]

    df["HT"] = df["HT"].apply(clean_amount)
    df["Taux"] = df["Taux"].apply(clean_amount)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d/%m/%Y")

    # ========================================================
    # ✅ REGROUPEMENT CORRECT PAR FACTURE
    # ========================================================
    df_factures = (
        df
        .groupby("Facture")
        .agg({
            "Date": "first",
            "Client": "first",
            "HT": "max",                 # 🔑 total HT facture
            "Taux": lambda x: list(set(x))
        })
        .reset_index()
    )

    # ========================================================
    # 🧾 GÉNÉRATION ÉCRITURES
    # ========================================================
    ecritures = []

    for _, row in df_factures.iterrows():
        ht = row["HT"]
        taux_list = row["Taux"]

        if ht == 0:
            continue

        # Multi taux → compte 704300
        if len(taux_list) == 1:
            taux = taux_list[0]
            compte_vte = compte_vente(taux)
            tva = round(ht * taux / 100, 2)
        else:
            taux = 0
            compte_vte = "704300000"
            tva = 0.0

        ttc = round(ht + tva, 2)

        compte_cli = compte_client(row["Client"])
        piece = row["Facture"]
        date = row["Date"]
        libelle = f"Facture {piece} - {row['Client']}"

        # Client
        ecritures.append({
            "Date": date,
            "Journal": "VT",
            "Numéro de compte": compte_cli,
            "Numéro de pièce": piece,
            "Libellé": libelle,
            "Débit": ttc,
            "Crédit": ""
        })

        # Vente
        ecritures.append({
            "Date": date,
            "Journal": "VT",
            "Numéro de compte": compte_vte,
            "Numéro de pièce": piece,
            "Libellé": libelle,
            "Débit": "",
            "Crédit": ht
        })

        # TVA uniquement si mono-taux
        if tva > 0:
            ecritures.append({
                "Date": date,
                "Journal": "VT",
                "Numéro de compte": "445740000",
                "Numéro de pièce": piece,
                "Libellé": libelle,
                "Débit": "",
                "Crédit": tva
            })

    df_out = pd.DataFrame(ecritures)

    # ========================================================
    # 📊 CONTRÔLES & EXPORT
    # ========================================================
    st.success(f"✅ {len(df_factures)} factures → {len(df_out)} écritures générées")

    total_debit = pd.to_numeric(df_out["Débit"], errors="coerce").sum()
    total_credit = pd.to_numeric(df_out["Crédit"], errors="coerce").sum()

    st.info(
        f"**Total Débit :** {total_debit:,.2f} € | "
        f"**Total Crédit :** {total_credit:,.2f} € | "
        f"**Écart :** {total_debit - total_credit:,.2f} €"
    )

    st.dataframe(df_out)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_out.to_excel(writer, index=False, sheet_name="Écritures")
    output.seek(0)

    st.download_button(
        "💾 Télécharger les écritures",
        data=output,
        file_name="ecritures_ventes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("⬆️ Charge un fichier Excel Factura pour commencer")
