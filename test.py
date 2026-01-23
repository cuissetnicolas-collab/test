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
    username_input = st.text_input("Identifiant")
    password_input = st.text_input("Mot de passe", type="password")
    if st.button("Connexion"):
        login(username_input, password_input)
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
    return float(str(x).replace("€","").replace("%","").replace(" ","").replace(",", "."))

def compte_client(nom):
    nom = str(nom).strip().upper()
    lettre = nom[0] if nom and nom[0].isalpha() else "X"
    return f"4110{lettre}0000"

def compte_vente(taux_unique=None, multi_tva=False):
    if multi_tva:
        return "704300000"
    mapping = {5.5:"704000000",10.0:"704100000",20.0:"704200000",0.0:"704500000"}
    return mapping.get(taux_unique,"704300000")

# ============================================================
# 🚀 TRAITEMENT FICHIER
# ============================================================
if uploaded_file:
    df = pd.read_excel(uploaded_file, dtype=str)
    df.columns = df.columns.str.strip()

    # Colonnes obligatoires
    required_cols = ["N° Facture", "Date", "Nom Facture", "Total HT", "Taux de tva"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"❌ Colonnes manquantes : {', '.join(missing)}")
        st.stop()

    df = df[required_cols].copy()
    df.columns = ["Facture","Date","Client","HT","Taux"]
    df["HT"] = df["HT"].apply(clean_amount)
    df["Taux"] = df["Taux"].apply(clean_amount)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d/%m/%Y")

    # ============================================================
    # 🔹 GENERATION DES ECRITURES PAR FACTURE
    # ============================================================
    ecritures = []

    for facture, group in df.groupby("Facture"):
        date = group["Date"].iloc[0]
        client = group["Client"].iloc[0]

        # Vérifier si plusieurs taux de TVA dans la facture
        taux_unique = group["Taux"].unique()
        multi_tva = len(taux_unique) > 1

        # Calcul HT total et TVA total
        ht_total = group["HT"].sum().round(2)
        tva_total = (group["HT"] * group["Taux"] / 100).sum().round(2)
        ttc_total = ht_total + tva_total

        libelle = f"Facture {facture} - {client}"
        compte_cli = compte_client(client)
        compte_vte = compte_vente(taux_unique=taux_unique[0] if not multi_tva else None, multi_tva=multi_tva)

        # 🔹 Débit client
        ecritures.append({
            "Date": date,
            "Journal": "VT",
            "Numéro de compte": compte_cli,
            "Numéro de pièce": facture,
            "Libellé": libelle,
            "Débit": ttc_total,
            "Crédit": ""
        })

        # 🔹 Crédit vente
        ecritures.append({
            "Date": date,
            "Journal": "VT",
            "Numéro de compte": compte_vte,
            "Numéro de pièce": facture,
            "Libellé": libelle,
            "Débit": "",
            "Crédit": ht_total
        })

        # 🔹 Crédit TVA
        if tva_total > 0.01:
            ecritures.append({
                "Date": date,
                "Journal": "VT",
                "Numéro de compte": "445740000",
                "Numéro de pièce": facture,
                "Libellé": libelle,
                "Débit": "",
                "Crédit": tva_total
            })

    df_out = pd.DataFrame(
        ecritures,
        columns=["Date","Journal","Numéro de compte","Numéro de pièce","Libellé","Débit","Crédit"]
    )

    # ============================================================
    # 📊 Contrôles & Export
    # ============================================================
    st.success(f"✅ {df['Facture'].nunique()} factures → {len(df_out)} écritures générées")

    total_debit = pd.to_numeric(df_out["Débit"], errors="coerce").sum()
    total_credit = pd.to_numeric(df_out["Crédit"], errors="coerce").sum()
    st.info(
        f"**Total Débit :** {total_debit:,.2f} € | "
        f"**Total Crédit :** {total_credit:,.2f} € | "
        f"**Écart :** {total_debit - total_credit:,.2f} €"
    )

    st.subheader("🔍 Aperçu des écritures")
    st.dataframe(df_out.head(20))

    # Export Excel
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
