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
    try:
        return float(
            str(x)
            .replace("€", "")
            .replace("%", "")
            .replace(" ", "")
            .replace(",", ".")
        )
    except:
        return 0.0

def compte_client(nom):
    nom = str(nom).strip().upper()
    lettre = nom[0] if nom and nom[0].isalpha() else "X"
    return f"4110{lettre}0000"

def compte_vente(taux, multi):
    if multi:
        return "704300000"
    mapping = {
        5.5: "704000000",
        10.0: "704100000",
        20.0: "704200000",
        0.0: "704500000"
    }
    return mapping.get(taux, "704300000")

# ============================================================
# 🚀 TRAITEMENT
# ============================================================
if uploaded_file:
    df = pd.read_excel(uploaded_file, dtype=str)
    df.columns = df.columns.str.strip()

    required_cols = [
        "N° Facture",
        "Date",
        "Nom Facture",
        "* Quantité",
        "Total HT d'origine sur quantité unitaire",
        "Total HT",
        "Taux de tva"
    ]

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"❌ Colonnes manquantes : {', '.join(missing)}")
        st.stop()

    df = df[required_cols]
    df.columns = [
        "Facture",
        "Date",
        "Client",
        "Qte",
        "HT_unitaire",
        "HT_facture",
        "Taux"
    ]

    # Nettoyage
    for col in ["Qte", "HT_unitaire", "HT_facture", "Taux"]:
        df[col] = df[col].apply(clean_amount)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d/%m/%Y")

    # Calcul HT ligne réel
    df["HT_ligne"] = (df["Qte"] * df["HT_unitaire"]).round(2)

    # ========================================================
    # 🧠 ANALYSE PAR FACTURE
    # ========================================================
    ecritures = []
    factures = df["Facture"].unique()

    for facture in factures:
        df_f = df[df["Facture"] == facture]

        date = df_f["Date"].iloc[0]
        client = df_f["Client"].iloc[0]
        compte_cli = compte_client(client)

        # HT facture (fourni par Factura)
        ht_facture = df_f["HT_facture"].iloc[0]

        # lignes exploitables uniquement
        lignes_valides = df_f[df_f["HT_ligne"] > 0]

        taux_valides = sorted(lignes_valides["Taux"].unique())

        # Détermination mono / multi
        if len(taux_valides) == 1:
            multi = False
            taux_final = taux_valides[0]
        else:
            multi = True
            taux_final = None

        # Calcul TVA
        if multi:
            tva = round(
    (lignes_valides["HT_ligne"] * lignes_valides["Taux"] / 100).sum(),
    2
)
        else:
            tva = round(ht_facture * taux_final / 100, 2)

        ttc = round(ht_facture + tva, 2)

        libelle = f"Facture {facture} - {client}"
        compte_vte = compte_vente(taux_final, multi)

        # Client
        ecritures.append({
            "Date": date,
            "Journal": "VT",
            "Numéro de compte": compte_cli,
            "Numéro de pièce": facture,
            "Libellé": libelle,
            "Débit": ttc,
            "Crédit": ""
        })

        # Vente
        ecritures.append({
            "Date": date,
            "Journal": "VT",
            "Numéro de compte": compte_vte,
            "Numéro de pièce": facture,
            "Libellé": libelle,
            "Débit": "",
            "Crédit": ht_facture
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
                "Crédit": tva
            })

    df_out = pd.DataFrame(
        ecritures,
        columns=[
            "Date", "Journal", "Numéro de compte",
            "Numéro de pièce", "Libellé", "Débit", "Crédit"
        ]
    )

    # ========================================================
    # 📊 CONTROLES & EXPORT
    # ========================================================
    total_debit = pd.to_numeric(df_out["Débit"], errors="coerce").sum()
    total_credit = pd.to_numeric(df_out["Crédit"], errors="coerce").sum()

    st.success(f"✅ {df['Facture'].nunique()} factures traitées")
    st.info(
        f"**Débit :** {total_debit:,.2f} € | "
        f"**Crédit :** {total_credit:,.2f} € | "
        f"**Écart :** {total_debit - total_credit:,.2f} €"
    )

    st.subheader("🔍 Aperçu")
    st.dataframe(df_out.head(20))

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
