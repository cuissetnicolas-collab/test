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
# 🧠 OUTILS
# ============================================================
def clean_amount(x):
    if pd.isna(x):
        return 0.0
    return float(str(x).replace("€", "").replace("%", "").replace(" ", "").replace(",", "."))

def compte_client(nom):
    nom = str(nom).strip().upper()
    lettre = nom[0] if nom and nom[0].isalpha() else "X"
    return f"4110{lettre}0000"

def compte_vente(taux, multi_tva):
    if multi_tva:
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
        "Taux de tva"
    ]

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Colonnes manquantes : {', '.join(missing)}")
        st.stop()

    df = df[required_cols]
    df.columns = ["Facture", "Date", "Client", "Qte", "HT_unitaire", "Taux"]

    df["Qte"] = df["Qte"].apply(clean_amount)
    df["HT_unitaire"] = df["HT_unitaire"].apply(clean_amount)
    df["Taux"] = df["Taux"].apply(clean_amount)
    df["HT_ligne"] = (df["Qte"] * df["HT_unitaire"]).round(2)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d/%m/%Y")

    # ========================================================
    # 🔁 REGROUPEMENT PAR FACTURE
    # ========================================================
    factures = []

    for facture, g in df.groupby("Facture"):
        ht_total = g["HT_ligne"].sum()
        taux_uniques = g["Taux"].unique()
        multi_tva = len(taux_uniques) > 1

        tva_total = sum((g[g["Taux"] == t]["HT_ligne"].sum() * t / 100) for t in taux_uniques)
        tva_total = round(tva_total, 2)
        ttc_total = round(ht_total + tva_total, 2)

        row = g.iloc[0]

        factures.append({
            "Facture": facture,
            "Date": row["Date"],
            "Client": row["Client"],
            "HT": round(ht_total, 2),
            "TVA": tva_total,
            "TTC": ttc_total,
            "Taux": taux_uniques[0],
            "MultiTVA": multi_tva
        })

    df_fact = pd.DataFrame(factures)

    # ========================================================
    # 🧾 ÉCRITURES
    # ========================================================
    ecritures = []

    for _, r in df_fact.iterrows():
        compte_cli = compte_client(r["Client"])
        compte_vte = compte_vente(r["Taux"], r["MultiTVA"])
        lib = f"Facture {r['Facture']} - {r['Client']}"

        ecritures += [
            {
                "Date": r["Date"], "Journal": "VT", "Numéro de compte": compte_cli,
                "Numéro de pièce": r["Facture"], "Libellé": lib,
                "Débit": r["TTC"], "Crédit": ""
            },
            {
                "Date": r["Date"], "Journal": "VT", "Numéro de compte": compte_vte,
                "Numéro de pièce": r["Facture"], "Libellé": lib,
                "Débit": "", "Crédit": r["HT"]
            }
        ]

        if r["TVA"] != 0:
            ecritures.append({
                "Date": r["Date"], "Journal": "VT", "Numéro de compte": "445740000",
                "Numéro de pièce": r["Facture"], "Libellé": lib,
                "Débit": "", "Crédit": r["TVA"]
            })

    df_out = pd.DataFrame(ecritures)

    st.success(f"✅ {len(df_fact)} factures traitées sans doublon")
    st.dataframe(df_out.head(15))

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
