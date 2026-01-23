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
    return float(str(x).replace("€","").replace("%","").replace(" ","").replace(",", "."))

def compte_client(nom):
    nom = str(nom).strip().upper()
    lettre = nom[0] if nom and nom[0].isalpha() else "X"
    return f"4110{lettre}0000"

def compte_vente(taux, multi_tva=False):
    if multi_tva:
        return "704300000"
    mapping = {5.5:"704000000",10.0:"704100000",20.0:"704200000",0.0:"704500000"}
    return mapping.get(taux,"704300000")

# ============================================================
# 🚀 TRAITEMENT FICHIER
# ============================================================
if uploaded_file:
    df = pd.read_excel(uploaded_file, dtype=str)
    df.columns = df.columns.str.strip()

    required_cols = ["N° Facture", "Date", "Nom Facture", "Total HT", "Taux de tva"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"❌ Colonnes manquantes : {', '.join(missing)}")
        st.stop()

    df = df[required_cols]
    df.columns = ["Facture","Date","Client","HT","Taux"]

    df["HT"] = df["HT"].apply(clean_amount)
    df["Taux"] = df["Taux"].apply(clean_amount)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d/%m/%Y")

    # ========================================================
    # 🔹 Détection factures multi-TVA
    # ========================================================
    multi_tva = df.groupby("Facture")["Taux"].nunique().reset_index()
    multi_tva["multi_tva"] = multi_tva["Taux"] > 1
    df = df.merge(multi_tva[["Facture","multi_tva"]], on="Facture", how="left")

    # ========================================================
    # 🔹 Regroupement par facture et par taux
    # ========================================================
    ecritures = []

    for facture, group in df.groupby("Facture"):
        date = group["Date"].iloc[0]
        client = group["Client"].iloc[0]
        multi = group["multi_tva"].iloc[0]

        # --- Débit client : somme de toutes les lignes TTC
        group["TVA_ligne"] = (group["HT"] * group["Taux"] / 100).round(2)
        ttc_total = (group["HT"] + group["TVA_ligne"]).sum().round(2)
        compte_cli = compte_client(client)
        libelle = f"Facture {facture} - {client}"

        ecritures.append({
            "Date": date,
            "Journal":"VT",
            "Numéro de compte": compte_cli,
            "Numéro de pièce": facture,
            "Libellé": libelle,
            "Débit": ttc_total,
            "Crédit": ""
        })

        # --- Crédit vente / HT
        if multi:
            ht_total = group["HT"].sum().round(2)
            compte_vte = "704300000"
            ecritures.append({
                "Date": date,
                "Journal":"VT",
                "Numéro de compte": compte_vte,
                "Numéro de pièce": facture,
                "Libellé": libelle,
                "Débit": "",
                "Crédit": ht_total
            })
            # TVA totale
            tva_total = group["TVA_ligne"].sum().round(2)
            if tva_total > 0.01:
                ecritures.append({
                    "Date": date,
                    "Journal":"VT",
                    "Numéro de compte":"445740000",
                    "Numéro de pièce": facture,
                    "Libellé": libelle,
                    "Débit": "",
                    "Crédit": tva_total
                })
        else:
            # facture avec un seul taux : groupe unique
            for taux, sous_groupe in group.groupby("Taux"):
                ht_total = sous_groupe["HT"].sum().round(2)
                tva_total = (ht_total * taux / 100).round(2)
                compte_vte = compte_vente(taux, multi)
                ecritures.append({
                    "Date": date,
                    "Journal":"VT",
                    "Numéro de compte": compte_vte,
                    "Numéro de pièce": facture,
                    "Libellé": libelle,
                    "Débit": "",
                    "Crédit": ht_total
                })
                if tva_total > 0.01:
                    ecritures.append({
                        "Date": date,
                        "Journal":"VT",
                        "Numéro de compte":"445740000",
                        "Numéro de pièce": facture,
                        "Libellé": libelle,
                        "Débit": "",
                        "Crédit": tva_total
                    })

    df_out = pd.DataFrame(ecritures, columns=["Date","Journal","Numéro de compte","Numéro de pièce","Libellé","Débit","Crédit"])

    # ========================================================
    # 📊 Contrôles & Export
    # ========================================================
    st.success(f"✅ {df['Facture'].nunique()} factures → {len(df_out)} écritures générées")

    total_debit = pd.to_numeric(df_out["Débit"], errors="coerce").sum()
    total_credit = pd.to_numeric(df_out["Crédit"], errors="coerce").sum()
    st.info(f"**Total Débit :** {total_debit:,.2f} € | **Total Crédit :** {total_credit:,.2f} € | **Écart :** {total_debit - total_credit:,.2f} €")

    st.subheader("🔍 Aperçu des écritures")
    st.dataframe(df_out.head(20))

    # --- Export Excel ---
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
