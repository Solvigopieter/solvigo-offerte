Solvigo Offertegenerator – Template
==================================

Wat zit erin?
-------------
- app.py               → Startpunt van de Streamlit-app (entrypoint).
- auth.py              → Wachtwoordscherm (één gedeeld wachtwoord via Streamlit Secrets).
- requirements.txt     → Benodigde Python-pakketten.
- .streamlit/secrets.toml → Lokaal wachtwoordbestand (optioneel voor lokaal testen).
- pages/
    01_PV Offerte.py   → Plak hier je robotische reinigings-offerte code.
    02_PV Manueel Offerte.py → Plak hier je manuele reinigings-offerte code.
- assets/              → Zet je afbeeldingen hier (bv. Logo.png, korstmos-foto’s).

Lokaal starten
--------------
pip install -r requirements.txt
streamlit run app.py

Online (Streamlit Community Cloud)
----------------------------------
- Repo op GitHub → Deploy met entrypoint: app.py
- In Settings → Secrets:
  APP_PASSWORD = "JullieSterkWachtwoord123!"