# pages/01_PV Offerte.py
from auth import require_login
require_login()

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from fpdf import FPDF
import io
import math
import os

# voorkom 'set_page_config can only be set once'
try:
    st.set_page_config(page_title="Offertegenerator Solvigo", layout="wide")
except Exception:
    pass

st.sidebar.success("PV-pagina geladen")  # smoke test, mag je weghalen
st.title("Solvigo Offertegenerator Zonnepanelenreiniging")
st.markdown("""
Vul hieronder de klantgegevens, parameters en opties in. Je ziet meteen het kostenoverzicht én kunt alles downloaden.
""")

# =========================
# Invoer: Klant & Basisopties
# =========================
col1, col2 = st.columns(2)
with col1:
    klantnaam = st.text_input("Klantnaam", "")
    klant_bedrijfsnaam = st.text_input("Bedrijfsnaam", "")
    klant_adres = st.text_area("Adres", "")
    offertedatum = st.date_input("Offertedatum", date.today())
    verloopdatum = st.date_input("Verloopdatum", date.today() + timedelta(days=60))
with col2:
    aantal_panelen = st.number_input("Aantal panelen", min_value=1, value=1)
    afstand_km = st.number_input("Afstand (km)", min_value=0, value=1)
    paneel_oppervlakte = st.number_input("Oppervlakte per paneel (m²)", min_value=1.0, value=2.0, step=0.1)
    aantal_robots = st.number_input("Aantal robots", min_value=1, value=1)
    zware_vervuiling = st.checkbox("Zware vervuiling", value=False)
    coating = st.checkbox("Optionele coating", value=True)

# =========================
# Parameters
# =========================
st.header("Parameters (belangrijkste eerst)")
col3, col4, col5 = st.columns(3)
with col3:
    minimum_tarief = st.number_input("Minimumtarief (€)", value=100.0)
    kosten_per_km = st.number_input("Kilometervergoeding (€ per km)", value=0.40)
    waterprijs_m3 = st.number_input("Osmosewater per m³ (€)", value=80.0)
    robot_panelen_per_dag = st.number_input("Robot: panelen per dag", value=2000)
    overhead_pct = st.number_input("Overhead (%)", min_value=0.0, max_value=1.0, value=0.20, step=0.01)
with col4:
    uurloon_op = st.number_input("Uurtarief operator (€)", value=70.0)
    u_per_dag = st.number_input("Uren per dag", value=8.0)
    robot_water_l_per_uur = st.number_input("Robot: waterverbruik per uur (L)", value=600)
    coating_prijs_per_5L = st.number_input("Coating: prijs per 5L (€)", value=350.0)
    coating_hoeveelheid_per_1000L = st.number_input("Coatinghoeveelheid per 1000L (L)", value=1.0)
with col5:
    borstel_life_panelen = st.number_input("Borstel: levensduur (panelen)", value=60000)
    borstel_prijs = st.number_input("Borstel: prijs (€)", value=200.0)
    borstels_per_robot = st.number_input("Borstels per robot", value=2)
    robot_prijs = st.number_input("Robot: aanschafprijs (€)", value=3500.0)
    robot_levensduur_panelen = st.number_input("Robot: levensduur (panelen)", value=500000)
    bat_duur_u = st.number_input("Batterij: werktijd (u)", value=3.5)
    bat_prijs = st.number_input("Batterij: prijs (€)", value=1000.0)
    bat_cycli = st.number_input("Batterij: cycli", value=500)

# =========================
# Opstart/Afbouw per dag
# =========================
st.subheader("Opstart/Afbouw per dag")
col6, col7 = st.columns(2)
with col6:
    opstart_dag1_u = st.number_input("Opstart dag 1 (u)", value=1.0, step=0.25)
    afbouw_dag1_u = st.number_input("Afbouw dag 1 (u)", value=0.5, step=0.25)
with col7:
    opstart_volgende_u = st.number_input("Opstart volgende dagen (u)", value=0.25, step=0.25)
    afbouw_volgende_u = st.number_input("Afbouw volgende dagen (u)", value=0.25, step=0.25)

# =========================
# Hoogtewerker
# =========================
st.subheader("Hoogtewerker")
hoogtewerker_gebruiken = st.checkbox("Hoogtewerker nodig?", value=False)
hoogtewerker_dagtarief = st.number_input("Hoogtewerker dagtarief (€)", value=0.0 if not hoogtewerker_gebruiken else 250.0, step=10.0)

# =========================
# Korstmos
# =========================
st.header("Korstmos behandeling (indien van toepassing)")
korstmos_aanwezig = st.checkbox("Korstmos aanwezig?", value=False)
aantal_korstmos_panelen = 0
gradatie_korstmos = "Licht"
if korstmos_aanwezig:
    aantal_korstmos_panelen = st.number_input("Aantal panelen met korstmos", min_value=1, value=min(50, int(aantal_panelen)), max_value=int(aantal_panelen))
    gradatie_korstmos = st.selectbox("Gradatie korstmos", ["Licht", "Gemiddeld", "Zwaar"], index=1)

PRODUCT_KG_PER_150M2 = 5
PRODUCT_PRIJS_PER_KG = st.number_input("Korstmosproduct prijs per kg (€)", value=35.0)
PRODUCT_KG_PER_M2 = PRODUCT_KG_PER_150M2 / 150

korstmos_product_kost = 0
korstmos_product_kg = 0
korstmos_arbeid_factor = 1.0
if korstmos_aanwezig:
    if gradatie_korstmos == "Licht":
        product_factor = 1.0
        korstmos_arbeid_factor = 2
    elif gradatie_korstmos == "Gemiddeld":
        product_factor = 1.5
        korstmos_arbeid_factor = 3
    else:
        product_factor = 2
        korstmos_arbeid_factor = 4

    totale_opp = aantal_korstmos_panelen * paneel_oppervlakte
    korstmos_product_kg = math.ceil(PRODUCT_KG_PER_M2 * totale_opp * product_factor)
    korstmos_product_kost = korstmos_product_kg * PRODUCT_PRIJS_PER_KG

# =========================
# Kernberekening
# =========================
def bereken_kosten_robot(
    aantal_panelen, afstand_km, opties, params,
    korstmos_aanwezig=False,
    aantal_korstmos_panelen=0,
    korstmos_product_kost=0,
    korstmos_product_kg=0,
    korstmos_arbeid_factor=1.0,
    paneel_oppervlakte=2.0,
    opstart_dag1_u=1.0,
    afbouw_dag1_u=0.5,
    opstart_volgende_u=0.25,
    afbouw_volgende_u=0.25,
    hoogtewerker_gebruiken=False,
    hoogtewerker_dagtarief=0.0
):
    f = 1.2 if opties.get('zware_vervuiling', False) else 1.0
    aantal_robots = opties.get('aantal_robots', 1)
    gewone_panelen = aantal_panelen - aantal_korstmos_panelen if korstmos_aanwezig else aantal_panelen

    robot_panelen_per_uur = params['robot_panelen_per_dag'] / params['u_per_dag']

    uren_cleaning_gewone = (gewone_panelen / (robot_panelen_per_uur * aantal_robots)) if gewone_panelen > 0 else 0.0
    uren_cleaning_korstmos = ((aantal_korstmos_panelen / (robot_panelen_per_uur * aantal_robots)) * korstmos_arbeid_factor) if korstmos_aanwezig else 0.0

    cleaning_uren = (uren_cleaning_gewone + uren_cleaning_korstmos) * f

    overhead_day1 = opstart_dag1_u + afbouw_dag1_u
    overhead_other = opstart_volgende_u + afbouw_volgende_u

    day1_capacity = max(params['u_per_dag'] - overhead_day1, 0.0)
    other_capacity = max(params['u_per_dag'] - overhead_other, 0.0)

    remaining = cleaning_uren
    dagen = 0
    overhead_totaal = 0.0

    if remaining > 0:
        dagen = 1
        consume = min(remaining, day1_capacity)
        remaining -= consume
        overhead_totaal += overhead_day1

    if remaining > 0:
        if other_capacity <= 0:
            extra_dagen = 1
        else:
            extra_dagen = math.ceil(remaining / other_capacity)
        dagen += extra_dagen
        overhead_totaal += extra_dagen * overhead_other

    tot_arb_u = cleaning_uren + overhead_totaal
    arb_kost = tot_arb_u * params['uurloon_op']

    veh_k_dag = afstand_km * params['kosten_per_km']
    trans_kost = dagen * veh_k_dag

    bor_k_per_paneel = (params['borstels_per_robot'] * params['borstel_prijs']) / params['borstel_life_panelen']
    bor_kost = aantal_panelen * bor_k_per_paneel * f

    bat_kost_per_cyclus = params['bat_prijs'] / params['bat_cycli']
    cycli = cleaning_uren / params['bat_duur_u']
    bat_kost = cycli * bat_kost_per_cyclus

    robot_afschrijving = (aantal_panelen / params['robot_levensduur_panelen']) * params['robot_prijs']

    extra_spoelbeurten = 2 if korstmos_aanwezig else 1
    total_water_l = (uren_cleaning_gewone * params['robot_water_l_per_uur']) + (uren_cleaning_korstmos * params['robot_water_l_per_uur'] * extra_spoelbeurten)
    osmose_m3 = total_water_l / 1000.0
    osmose_kost = osmose_m3 * params['waterprijs_m3']

    totale_opp_paneel = aantal_panelen * paneel_oppervlakte
    coating_liters = (totale_opp_paneel / 1000.0) * params['coating_hoeveelheid_per_1000L']
    coating_literprijs = params['coating_prijs_per_5L'] / 5.0
    coating_prijs = coating_liters * coating_literprijs if opties.get('coating', True) else 0.0

    hoogtewerker_kost = (hoogtewerker_dagtarief * dagen) if hoogtewerker_gebruiken else 0.0

    dir_kost = arb_kost + bor_kost + bat_kost + osmose_kost + robot_afschrijving
    overhead = dir_kost * params['overhead_pct']
    reiniging_totaal = dir_kost + overhead
    totaal = reiniging_totaal + trans_kost + korstmos_product_kost + hoogtewerker_kost
    totaal = max(round(totaal, 2), params['minimum_tarief'])

    return {
        'totaal': totaal,
        'reiniging_totaal': round(reiniging_totaal, 2),
        'transportkost': round(trans_kost, 2),
        'uren_cleaning': round(cleaning_uren, 2),
        'werkuren': round(tot_arb_u, 2),
        'dagen': int(dagen),
        'kost_per_paneel': round(reiniging_totaal / aantal_panelen, 2),
        'osmose_kost': round(osmose_kost, 2),
        'bor_kost': round(bor_kost, 2),
        'bat_kost': round(bat_kost, 2),
        'overhead': round(overhead, 2),
        'robot_afschrijving': round(robot_afschrijving, 2),
        'arb_kost': round(arb_kost, 2),
        'coating_prijs': round(coating_prijs, 2),
        'coating_liters': round(coating_liters, 2),
        'korstmos_product_kost': round(korstmos_product_kost, 2),
        'korstmos_product_kg': korstmos_product_kg,
        'hoogtewerker_kost': round(hoogtewerker_kost, 2),
        'overhead_day1': round(overhead_day1, 2),
        'overhead_other': round(overhead_other, 2),
        'day1_capacity': round(day1_capacity, 2),
        'other_capacity': round(other_capacity, 2),
    }

params = {
    'minimum_tarief': minimum_tarief,
    'kosten_per_km': kosten_per_km,
    'robot_panelen_per_dag': robot_panelen_per_dag,
    'u_per_dag': u_per_dag,
    'borstel_life_panelen': borstel_life_panelen,
    'borstel_prijs': borstel_prijs,
    'borstels_per_robot': borstels_per_robot,
    'bat_duur_u': bat_duur_u,
    'bat_prijs': bat_prijs,
    'bat_cycli': bat_cycli,
    'uurloon_op': uurloon_op,
    'overhead_pct': overhead_pct,
    'robot_prijs': robot_prijs,
    'robot_levensduur_panelen': robot_levensduur_panelen,
    'waterprijs_m3': waterprijs_m3,
    'robot_water_l_per_uur': robot_water_l_per_uur,
    'coating_prijs_per_5L': coating_prijs_per_5L,
    'coating_hoeveelheid_per_1000L': coating_hoeveelheid_per_1000L
}
opties = {
    'aantal_robots': aantal_robots,
    'zware_vervuiling': zware_vervuiling,
    'coating': coating
}

resultaat = bereken_kosten_robot(
    aantal_panelen, afstand_km, opties, params,
    korstmos_aanwezig=korstmos_aanwezig,
    aantal_korstmos_panelen=aantal_korstmos_panelen,
    korstmos_product_kost=korstmos_product_kost,
    korstmos_product_kg=korstmos_product_kg,
    korstmos_arbeid_factor=korstmos_arbeid_factor,
    paneel_oppervlakte=paneel_oppervlakte,
    opstart_dag1_u=opstart_dag1_u,
    afbouw_dag1_u=afbouw_dag1_u,
    opstart_volgende_u=opstart_volgende_u,
    afbouw_volgende_u=afbouw_volgende_u,
    hoogtewerker_gebruiken=hoogtewerker_gebruiken,
    hoogtewerker_dagtarief=hoogtewerker_dagtarief
)

# =========================
# Kostenverdeling tabel
# =========================
kosten_rows = [
    {"Omschrijving": "Werkuren (incl. opstart/afbouw)", "Bedrag (EUR)": resultaat['werkuren']},
    {"Omschrijving": "Aantal dagen (info)", "Bedrag (EUR)": resultaat['dagen']},
    {"Omschrijving": "Arbeidskost", "Bedrag (EUR)": resultaat['arb_kost']},
    {"Omschrijving": "Borstelslijtage", "Bedrag (EUR)": resultaat['bor_kost']},
    {"Omschrijving": "Batterijslijtage", "Bedrag (EUR)": resultaat['bat_kost']},
    {"Omschrijving": "Robot-afschrijving", "Bedrag (EUR)": resultaat['robot_afschrijving']},
    {"Omschrijving": "Osmosewater-kost", "Bedrag (EUR)": resultaat['osmose_kost']},
    {"Omschrijving": "Overhead", "Bedrag (EUR)": resultaat['overhead']},
    {"Omschrijving": "Reiniging totaal (incl. overhead)", "Bedrag (EUR)": resultaat['reiniging_totaal']},
    {"Omschrijving": "Transportkost", "Bedrag (EUR)": resultaat['transportkost']},
]
if hoogtewerker_gebruiken:
    kosten_rows.append({"Omschrijving": "Hoogtewerker", "Bedrag (EUR)": resultaat['hoogtewerker_kost']})
if korstmos_aanwezig:
    kosten_rows.append({"Omschrijving": "Korstmos product", "Bedrag (EUR)": resultaat['korstmos_product_kost']})

kosten_rows.extend([
    {"Omschrijving": "Totale kost", "Bedrag (EUR)": resultaat['totaal']},
    {"Omschrijving": "Kost per paneel", "Bedrag (EUR)": resultaat['kost_per_paneel']},
    {"Omschrijving": "Optioneel: Coating", "Bedrag (EUR)": resultaat['coating_prijs']},
])
kosten_df = pd.DataFrame(kosten_rows)
st.subheader("Kostenverdeling")
st.table(kosten_df)

# =========================
# Excel export (alleen .xlsx)
# =========================
def maak_excel():
    df_dict = {
        'Klantnaam': klantnaam,
        'Bedrijfsnaam': klant_bedrijfsnaam,
        'Adres': klant_adres,
        'Aantal panelen': aantal_panelen,
        'Afstand (km)': afstand_km,
        'Paneelgrootte (m²)': paneel_oppervlakte,
        'Werkuren (incl. op/afbouw)': resultaat['werkuren'],
        'Cleaning-uren (zonder op/afbouw)': resultaat['uren_cleaning'],
        'Aantal dagen': resultaat['dagen'],
        'Transportkost (EUR)': resultaat['transportkost'],
        'Osmosewater-kost (EUR)': resultaat['osmose_kost'],
        'Arbeidskost (EUR)': resultaat['arb_kost'],
        'Borstelslijtage (EUR)': resultaat['bor_kost'],
        'Batterijslijtage (EUR)': resultaat['bat_kost'],
        'Robot-afschrijving (EUR)': resultaat['robot_afschrijving'],
        'Overhead (EUR)': resultaat['overhead'],
        'Reiniging totaal (EUR)': resultaat['reiniging_totaal'],
        'Hoogtewerker (EUR)': resultaat['hoogtewerker_kost'],
        'Totale kost (EUR)': resultaat['totaal'],
        'Kost per paneel (EUR)': resultaat['kost_per_paneel'],
        'Optioneel: Coating (EUR)': resultaat['coating_prijs'],
        'Coating hoeveelheid (L)': resultaat['coating_liters'],
        'Opstart dag 1 (u)': opstart_dag1_u,
        'Afbouw dag 1 (u)': afbouw_dag1_u,
        'Opstart volgende dagen (u)': opstart_volgende_u,
        'Afbouw volgende dagen (u)': afbouw_volgende_u,
        'Dag 1 cleaning-capaciteit (u)': resultaat['day1_capacity'],
        'Volgende dagen cleaning-capaciteit (u)': resultaat['other_capacity'],
    }
    if korstmos_aanwezig:
        df_dict['Korstmos product (EUR)'] = resultaat['korstmos_product_kost']
        df_dict['Korstmos product (kg)'] = resultaat['korstmos_product_kg']
        df_dict['Aantal panelen met korstmos'] = aantal_korstmos_panelen
        df_dict['Gradatie korstmos'] = gradatie_korstmos
    df = pd.DataFrame([df_dict])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Offerte")
        kosten_df.to_excel(writer, index=False, sheet_name="Kostenverdeling")
    return output.getvalue()

# =========================
# PDF export (optioneel)
# =========================
def maak_pdf():
    from fpdf import FPDF
    import os

    pdf = FPDF()
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- Fonts ---
    use_unicode = False
    try:
        if os.path.exists("DejaVuSans.ttf"):
            pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
            pdf.set_font("DejaVu", "", 11)
            use_unicode = True
        else:
            pdf.set_font("Helvetica", size=11)
    except Exception:
        pdf.set_font("Helvetica", size=11)

    # --- Logo + bedrijfsinfo ---
    logo_x, logo_y, logo_w = 140, 15, 50
    try:
        pdf.image("Logo.png", x=logo_x, y=logo_y, w=logo_w)
    except Exception:
        pass
    logo_h = logo_w * 1.0

    bedrijfsinfo = [
        "Solvigo (BV)",
        "Baksveld 38, 2260 Westerlo",
        "Tel.: 0471425669",
        "Btw-nr: BE 0677.778.392",
        "IBAN: BE59 0018 1682 5558",
        "www.solvigo.be",
        "cleaning@solvigo.be",
    ]
    bedrijfsinfo_y = logo_y + logo_h + 2
    pdf.set_font("DejaVu" if use_unicode else "Helvetica", size=11)
    for i, lijn in enumerate(bedrijfsinfo):
        pdf.set_xy(logo_x, bedrijfsinfo_y + i * 6)
        pdf.cell(0, 6, lijn, align="L")

    # --- Titel ---
    pdf.set_y(30)
    pdf.set_font("DejaVu" if use_unicode else "Helvetica", "B", 22)
    pdf.cell(0, 12, "Offerte", ln=1)

    # --- Offertedetails ---
    left_x = pdf.l_margin
    pdf.set_xy(left_x, bedrijfsinfo_y)

    pdf.set_font("DejaVu" if use_unicode else "Helvetica", "B", 13)
    pdf.cell(0, 8, "Offertedetails", ln=1)
    pdf.set_font("DejaVu" if use_unicode else "Helvetica", "", 10)
    details = [
        f"Offertedatum: {offertedatum:%d-%m-%Y}",
        "Offertenummer: 1",
        f"Verloopdatum: {verloopdatum:%d-%m-%Y}",
    ]
    for d in details:
        pdf.cell(0, 6, d, ln=1)

    # --- Klantinformatie ---
    pdf.set_font("DejaVu" if use_unicode else "Helvetica", "B", 13)
    pdf.cell(0, 8, "Klantinformatie", ln=1)
    pdf.set_font("DejaVu" if use_unicode else "Helvetica", "", 11)
    if klant_bedrijfsnaam.strip():
        pdf.cell(0, 6, klant_bedrijfsnaam, ln=1)
    for regel in klant_adres.split("\n"):
        if regel.strip():
            pdf.cell(0, 6, regel, ln=1)

    left_bottom = pdf.get_y()
    right_block_bottom = bedrijfsinfo_y + len(bedrijfsinfo) * 6
    header_bottom = max(logo_y + logo_h, right_block_bottom)
    flow_bottom = max(left_bottom, header_bottom)
    pdf.set_y(flow_bottom + 8)

    # --- Intro tekst ---
    pdf.set_font("DejaVu" if use_unicode else "Helvetica", "", 10)
    info_tekst = (
        "Wij waarderen uw keuze voor Solvigo! Uw panelen worden efficiënt gereinigd met robottechnologie. "
        "Voor extra bescherming en langdurige reinheid adviseren wij de optionele antistatische coating. "
        "Zo blijft uw investering maximaal renderen."
    )
    pdf.multi_cell(0, 5, info_tekst)
    pdf.ln(6)

    # --- Kernrij helper ---
    label_w, value_w = 75, 40
    def kernrij(label, value, bold=False):
        pdf.set_font("DejaVu" if use_unicode else "Helvetica", "", 10)
        pdf.cell(label_w, 7, label, align="L")
        pdf.set_font("DejaVu" if use_unicode else "Helvetica", "B" if bold else "", 11)
        pdf.cell(value_w, 7, value, ln=1, align="L")

    kernrij("Aantal zonnepanelen:", f"{aantal_panelen:,}".replace(",", "."), bold=True)
    kernrij("Werkuren (incl. opstart/afbouw):", f"{resultaat['werkuren']} uur", bold=True)
    kernrij("Aantal dagen:", f"{resultaat['dagen']}", bold=True)
    pdf.ln(6)

    # --- Voorwaarden voor uitvoering ---
    pdf.set_font("DejaVu" if use_unicode else "Helvetica", "B", 8)
    pdf.set_text_color(200, 0, 0)
    pdf.multi_cell(
        0,
        6,
        "Opdrachtgever voorziet een 230V 20A stopcontact en een wateraansluiting met een debiet van minimaal 8L/minuut (standaard) of hoger nabij de installatie."
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    # --- Kostenoverzicht ---
    pdf.set_font("DejaVu" if use_unicode else "Helvetica", "B", 12)
    pdf.cell(0, 8, "Kostenoverzicht", ln=1)
    pdf.set_font("DejaVu" if use_unicode else "Helvetica", "", 10)
    pdf.set_fill_color(245, 245, 245)
    pdf.set_draw_color(120, 120, 120)
    pdf.set_line_width(0.4)

    def row(hdr, qty, unit, total):
        pdf.cell(60, 8, hdr, border=1)
        pdf.cell(35, 8, qty, border=1, align="C")
        pdf.cell(38, 8, unit, border=1, align="C")
        pdf.cell(37, 8, total, border=1, align="R")
        pdf.ln(8)

    pdf.cell(60, 8, "Omschrijving", border=1, align="L", fill=True)
    pdf.cell(35, 8, "Aantal/Afstand", border=1, align="C", fill=True)
    pdf.cell(38, 8, "Prijs per eenheid", border=1, align="C", fill=True)
    pdf.cell(37, 8, "Totaal", border=1, align="R", fill=True)
    pdf.ln(8)

    row("Reiniging zonnepanelen", f"{aantal_panelen} stuks", f"{resultaat['kost_per_paneel']:.2f} EUR/paneel", f"{resultaat['reiniging_totaal']:.2f} EUR")
    row("Verplaatsingskosten", f"{afstand_km} km x {resultaat['dagen']} d", f"{kosten_per_km:.2f} EUR/km", f"{resultaat['transportkost']:.2f} EUR")
    if korstmos_aanwezig:
        row("Korstmos product", f"{resultaat['korstmos_product_kg']} kg", f"{PRODUCT_PRIJS_PER_KG:.2f} EUR/kg", f"{resultaat['korstmos_product_kost']:.2f} EUR")
    if hoogtewerker_gebruiken:
        row("Hoogtewerker", f"{resultaat['dagen']} d", f"{hoogtewerker_dagtarief:.2f} EUR/dag", f"{resultaat['hoogtewerker_kost']:.2f} EUR")

    pdf.ln(6)

    # --- Optioneel coating ---
    pdf.set_draw_color(120, 120, 120)
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font("DejaVu" if use_unicode else "Helvetica", "B", 11)
    pdf.cell(170, 8, "Optioneel: Antistatische coating", border=1, align="C", fill=True)
    pdf.ln(8)
    pdf.set_font("DejaVu" if use_unicode else "Helvetica", "", 10)
    pdf.cell(85, 8, f"Hoeveelheid: {resultaat['coating_liters']:.2f} L", border=1, align="L", fill=True)
    pdf.cell(85, 8, f"Totaalprijs: {resultaat['coating_prijs']:.2f} EUR", border=1, align="L", fill=True)
    pdf.ln(10)

    # --- Totaal excl/incl btw ---
    totaal_excl_btw = resultaat["reiniging_totaal"] + resultaat["transportkost"]
    if korstmos_aanwezig:
        totaal_excl_btw += resultaat["korstmos_product_kost"]
    if hoogtewerker_gebruiken:
        totaal_excl_btw += resultaat["hoogtewerker_kost"]
    btw = 0.00
    pdf.set_font("DejaVu" if use_unicode else "Helvetica", "B", 11)
    pdf.cell(0, 7, f"Bedrag excl. BTW: {totaal_excl_btw:.2f} EUR", align="R")
    pdf.ln(7)
    pdf.set_font("DejaVu" if use_unicode else "Helvetica", "B", 10)
    pdf.cell(0, 7, f"BTW (0%): {btw:.2f} EUR", align="R")
    pdf.ln(7)
    pdf.set_font("DejaVu" if use_unicode else "Helvetica", "B", 12)
    pdf.cell(0, 8, f"Totaal incl. BTW: {totaal_excl_btw + btw:.2f} EUR", align="R")
    pdf.ln(10)

    # --- Nieuwe pagina: Algemene Voorwaarden ---
    pdf.add_page()
    pdf.set_font("DejaVu" if use_unicode else "Helvetica", "B", 12)
    pdf.cell(0, 10, "Algemene Voorwaarden - Solvigo BV", ln=1)
    pdf.ln(2)

    voorwaarden = """
1. Toepasselijkheid
1.1 Deze voorwaarden zijn van toepassing op alle offertes, overeenkomsten en werkzaamheden uitgevoerd door Solvigo BV, hierna "de dienstverlener" genoemd.
1.2 Afwijkingen van deze voorwaarden zijn alleen geldig indien schriftelijk overeengekomen.

2. Diensten en uitvoering
2.1 De dienstverlener reinigt met zorg en volgens professionele normen, doch levert een inspanningsverbintenis en geen resultaatsverbintenis.
2.2 De dienstverlener behoudt zich het recht voor om opdrachten te weigeren of stop te zetten indien een veilige of kwalitatieve uitvoering niet kan worden gegarandeerd.
2.3 Bij extreme verontreiniging of onbereikbare plaatsen kan een herziening van de prijs of planning worden voorgesteld.

3. Prijzen en betalingen
3.1 Alle prijzen zijn exclusief btw, tenzij anders vermeld.
3.2 Verplaatsingskosten worden apart in rekening gebracht volgens de geldende tarieven.
3.3 De dienstverlener mag prijzen aanpassen bij stijging van index, brandstof, taksen of materiaalkosten.
3.4 Betaling dient te geschieden binnen de veertien (14) dagen na factuurdatum, tenzij anders overeengekomen.

4. Verantwoordelijkheden klant
4.1 De klant zorgt voor vrije en veilige toegang tot de werf, voldoende parkeergelegenheid, alsook de vereiste nutsvoorzieningen, zoals regenwater (met voldoende debiet en druk) en elektriciteit, tenzij uitdrukkelijk anders overeengekomen.
4.2 De klant voorziet alle nodige vergunningen, veiligheidsmaatregelen, en meldt vooraf de aanwezigheid van kwetsbare of defecte delen of installaties.
4.3 De klant draagt zorg voor het vrijmaken van de werkzone, het afsluiten van ramen/deuren/screens en het correct in- of uitschakelen van toestellen indien nodig.
4.4 De klant staat in voor de afvoer van afval en restproducten, tenzij uitdrukkelijk anders overeengekomen.

5. Aansprakelijkheid
5.1 De dienstverlener is uitsluitend aansprakelijk voor directe schade veroorzaakt door grove nalatigheid of opzet.
5.2 De dienstverlener is niet aansprakelijk voor:
- waterschade, kortsluitingen, productieverlies, schade aan bekabeling, leidingen, elektronica, machines of regelapparatuur, coatings, vliegroest, lekken, scheuren, verkleuring of afschilfering van oppervlakken,
- schade door niet-tijdige of onvolledige informatie,
- schade aan bestaande gebreken of slijtage,
- schade door gebruik van door de klant aangeleverde materialen, toestellen of middelen,
- indirecte schade, gevolgschade of gederfde winst.
5.3 De totale aansprakelijkheid van de dienstverlener is beperkt tot het bedrag van de factuur voor de betreffende opdracht.

6. Garanties en uitzonderlijke omstandigheden
6.1 De dienstverlener biedt geen garanties op schoonmaakresultaten in gevallen van hardnekkige vlekken, blijvende aanslag, of aangetaste oppervlakken.
6.2 Bij overmacht of niet-voorzienbare omstandigheden (zoals weersomstandigheden, technische storingen, onveilige situaties, ...) kan de opdracht verplaatst of geannuleerd worden zonder recht op schadevergoeding.
6.3 Indien resultaat niet haalbaar blijkt met voorziene technologie, kan in overleg een nieuw voorstel gedaan worden; reeds geleverde prestaties worden verrekend.

7. Annulering
7.1 Annulering dient schriftelijk te gebeuren uiterlijk achtenveertig (48) uur voor de afgesproken datum.
7.2 Bij latere annulering kan tot 50% van de offerteprijs of de minimum daginzet in rekening gebracht worden.
7.3 Bij uitstel, wachttijd of vertraging buiten de wil van de dienstverlener worden extra uren aangerekend volgens regietarief.

8. Documentatie & communicatie
8.1 De dienstverlener mag foto's nemen voor, tijdens en na de werken voor rapportering, bewijs en interne kwaliteitsopvolging.
8.2 De dienstverlener heeft het recht om bescheiden reclame te plaatsen op de werf tijdens de uitvoering.

9. Geschillen en toepasselijk recht
9.1 Op alle overeenkomsten is het Belgisch recht van toepassing.
9.2 Geschillen worden bij voorkeur in onderling overleg opgelost. Indien dit niet mogelijk is, worden ze voorgelegd aan de bevoegde rechter van het arrondissement waar de dienstverlener is gevestigd.

10. Wijzigingen
10.1 De dienstverlener behoudt zich het recht voor deze voorwaarden te wijzigen. Klanten worden tijdig geïnformeerd over wijzigingen.
""".strip()

    pdf.set_font("DejaVu" if use_unicode else "Helvetica", "", 8)
    for par in voorwaarden.split("\n\n"):
        pdf.multi_cell(0, 4, par)
        pdf.ln(1)

    return bytes(pdf.output(dest="S"))


col_download1, col_download2 = st.columns(2)
with col_download1:
    st.download_button(
        label="Download Excel",
        data=maak_excel(),
        file_name=f"Offerte_{klantnaam.replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
with col_download2:
    st.download_button(
        label="Download PDF",
        data=maak_pdf(),
        file_name=f"Offerte_{klantnaam.replace(' ', '_')}.pdf",
        mime="application/pdf"
    )

st.info("Tip: wijzig een parameter hierboven en zie direct het nieuwe kostenoverzicht.")
