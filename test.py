import streamlit as st
import streamlit_authenticator as stauth

config = {
    "credentials": {
        "usernames": {
            "expert1": {
                "email": "expert1@mail.com",
                "name": "Expert Comptable 1",
                # mot de passe "12345" hashé
                "password": "$2b$12$kLKNnTOplTQ4DZVmFJb1YulMxoF1BCGYnH3o.KnQIzW5nbLqV/2ZW"
            }
        }
    },
    "cookie": {"expiry_days": 1, "key": "cookie_signature", "name": "auth_cookie"},
    "preauthorized": {}
}

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# appel simple
name, authentication_status, username = authenticator.login()

if authentication_status:
    authenticator.logout("Déconnexion", "sidebar")
    st.sidebar.success(f"Bienvenue {name} 👋")
elif authentication_status is False:
    st.error("❌ Identifiants incorrects")
elif authentication_status is None:
    st.warning("🔑 Veuillez entrer vos identifiants")