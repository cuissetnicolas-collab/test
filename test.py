import streamlit as st
import pandas as pd

# =========================
# CONFIG PAGE
# =========================
st.set_page_config(
    page_title="Générateur écritures comptables",
    layout="wide"
)

# =========================
# AUTHENTIFICATION SIMPLE
# =========================
USERS = {
    "admin": "admin123",
    "compta": "compta123"
}

def login():
    st.title("🔐 Connexion")

    username = st.text_input("Utilisateur")
    password = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter"):
        if username in USERS and USERS[username] == password:
            st.session_state["authenticated"] = True
            st.session_state["user"] = username
            st.success("Connexion réussie")
            st.rerun()
        else:
            st.error("Identifiants incorrects")

def logout():
    st.session_state.clear()
    st.rerun()

# =========================
# PAGE PRINCIPALE
# =========================
def app():
    st.title("📊 Générateur d’écritures comptables")

    st.sidebar.success(f"Connecté : {st.session_state['user']}")
    if st.sidebar.button("Se déconnecter"):
        logout()

    st.markdown("### 📂 Import du fichier de ventes")

    uploaded_file = st.file_uploader(
        "Importer le fichier Excel",
        type=["xlsx"]
    )

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.success("Fichier chargé avec succès")

        st.markdown("### 👀 Aperçu des données")
        st.dataframe(df.head(20))

        if st.button("🚀 Générer les écritures"):
            # =========================
            # 👉 ICI TU RECOLLES TON CODE EXISTANT
            # =========================

            # Exemple temporaire
            result = df.copy()

            st.markdown("### 📄 Résultat")
            st.dataframe(result)

            st.download_button(
                "⬇️ Télécharger le fichier",
                data=result.to_csv(index=False, sep=";", decimal=","),
                file_name="ecritures_comptables.csv",
                mime="text/csv"
            )

# =========================
# ROUTING
# =========================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login()
else:
    app()
