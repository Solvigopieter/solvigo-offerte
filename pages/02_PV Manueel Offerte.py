from auth import require_login
require_login()

# pages/02_PV Manueel Offerte.py
import streamlit as st
import pandas as pd
import math
from datetime import date, timedelta
from fpdf import FPDF
import io

# -- voorkom 'set_page_config can only be set once'
try:
    st.set_page_config(page_title="Offertegenerator Solvigo (Manueel)", layout="wide")
except Exception:
    pass

st.sidebar.success("Manueel-pagina geladen")
st.title("Solvigo Offertegenerator Zonnepanelenreiniging – Manueel")

st.markdown(
    "Vul hieronder de klantgegevens, parameters en opties in. "
    "Je ziet meteen het kostenoverzicht en kan **Excel (.xlsx)** en **PDF** downloaden."
)

# ------------------ Unicode-fix functie ------------------
def vervang_unicode_tekens(tekst):
    vervangingen = {
        "“": '"', "”": '"', "‘": "'", "’": "'",
        "–": "-", "—": "-", "…": "...", "•": "-", "€": "EUR",
        "\u00A0": " ", "\u2011":"-", "\u2010":"-", "\u202F":" ", "\u2009":" ", "\u200A":" ", "\u2007":" "
    }
    if isinstance(tekst, str):
        for oud, nieuw in vervangingen.items():
            tekst = tekst.replace(oud, nieuw)
    return tekst

# ================= ALGEMENE BEDRIJFSINSTELLINGEN ==================
COMPANY_CONFIG = {
    "bedrijf": "Solvigo (BV)",
    "adres": "Baksveld 38, 2260 Westerlo",
    "tel": "0471425669",
    "btw": "BE 0677.778.392",
    "iban": "BE59 0018 1682 5558",
    "kbo": "0123456789",
    "www": "www.solvigo.be",
    "mail": "cleaning@solvigo.be"
}

# ===================== BASIS-INVOER =====================
colA, colB = st.columns(2)
with colA:
    klantnaam = st.text_input("Klantnaam", "")
    klant_bedrijfsnaam = st.text_input("Bedrijfsnaam", "")
    klant_adres = st.text_area("Adres", "")
    offertedatum = st.date_input("Offertedatum", date.today())
    verloopdatum = st.date_input("Verloopdatum", date.today() + timedelta(days=60))
with colB:
    aantal_panelen = st.number_input("Aantal panelen", min_value=1, value=500, step=10)
    afstand_km = st.number_input("Afstand (km) enkele rit", min_value=0, value=25, step=1)
    dak_type = st.selectbox("Daktype", ["plat", "schuin"])
    onderhoudscontract = st.checkbox("Onderhoudscontract (4×/jaar) – 15% korting", value=False)

# ===================== PARAMETERS & TARIEVEN ======================
st.header("Parameters & Tarieven")
c1, c2, c3, c4 = st.columns(4)
with c1:
    minimum_tarief = st.number_input("Minimumtarief (€)", value=100.0, step=10.0)
    afstandskosten_per_km = st.number_input("Kilometervergoeding (€ per km)", value=0.40, step=0.05)
    uurtarief = st.number_input("Uurtarief per persoon (€)", value=50.0, step=5.0)
with c2:
    aantal_personen = st.number_input("Aantal personen (voor berekening)", min_value=1, value=2)
    overhead_percentage = st.number_input("Overhead (%) (0–1)", min_value=0.0, max_value=1.0, value=0.20, step=0.01)
    btw_percentage = st.number_input("BTW (%) (0–1)", min_value=0.0, max_value=1.0, value=0.0, step=0.01)
with c3:
    max_werkuren_per_dag = st.number_input("Max werkuren per dag", min_value=1.0, value=10.0, step=0.5)
    opstart_afbouw_per_dag = st.number_input("Opstart + afbouw per dag (uur)", min_value=0.0, value=0.5, step=0.25)
    waterbron = st.selectbox("Waterbron", ["osmose", "leiding (geen osmosekost)"])
with c4:
    hoogtewerker_kost_per_dag = st.number_input("Hoogtewerker dagtarief (€)", value=200.0, step=10.0)
    mobiel_ankerpunt_kost_per_dag = st.number_input("Mobiel ankerpunt dagtarief (€)", value=100.0, step=10.0)

# ===================== SNELHEID (panelen/uur per persoon) ======================
st.subheader("Snelheid (panelen per uur per persoon)")
sp1, sp2 = st.columns(2)
with sp1:
    snelheid_plat_ppu = st.number_input("Manueel: panelen/uur (plat)", min_value=1, value=90, step=5)
with sp2:
    snelheid_schuin_ppu = st.number_input("Manueel: panelen/uur (schuin)", min_value=1, value=75, step=5)

# ===================== PRODUCT- EN MATERIAALKOSTEN ================
st.subheader("Product- & materiaalkosten")
p1, p2, p3 = st.columns(3)
with p1:
    kosten_osmose_water_per_m3 = st.number_input("Osmosewater per m³ (€)", value=70.0, step=5.0)
    paneel_oppervlakte_m2 = st.number_input("Paneeloppervlakte (m²)", min_value=0.1, value=1.8, step=0.1)
    coating_prijs_per_5L = st.number_input("Coating prijs per 5L (€)", value=350.0, step=10.0)
with p2:
    coating_hoeveelheid_per_1000L = st.number_input("Coatinghoeveelheid per 1000L (L)", min_value=0.0, value=1.0, step=0.1)
    verhouding_product_naar_osmose_water = st.number_input("Mengverhouding (1L product per X L water)", min_value=1, value=500, step=50)
    korstmos_product_kostprijs = st.number_input("Korstmosproduct (€/bus)", value=25.0, step=1.0)
with p3:
    korstmos_product_dekking_m2 = st.number_input("Korstmos dekking (m² per bus)", min_value=1.0, value=150.0, step=10.0)
    vogeluitwerpselen_product_kostprijs_per_liter = st.number_input("Vogeluitwerpselen product (€/L)", value=18.0, step=1.0)
    hardnekkig_vuil_product_kostprijs_per_liter = st.number_input("Hardnekkig vuil product (€/L)", value=20.0, step=1.0)

st.subheader("Tijds-factoren")
tf1, tf2 = st.columns(2)
with tf1:
    extra_tijd_korstmos_factor = st.number_input("Extra tijd: korstmos (×)", min_value=1.0, value=3.0, step=0.1)
    extra_tijd_vogeluitwerpselen_factor = st.number_input("Extra tijd: vogeluitwerpselen (×)", min_value=1.0, value=1.3, step=0.1)
with tf2:
    extra_tijd_hardnekkig_factor = st.number_input("Extra tijd: hardnekkig vuil (×)", min_value=1.0, value=1.5, step=0.1)
    extra_tijd_stoflaag_factor = st.number_input("Extra tijd: stoflaag (×)", min_value=1.0, value=1.2, step=0.1)

# ===================== OPTIES / OMSTANDIGHEDEN =====================
st.header("Site-opties en omstandigheden")
o1, o2, o3, o4 = st.columns(4)
with o1:
    optie_korstmos = st.checkbox("Korstmos aanwezig", value=False)
    optie_vogel = st.checkbox("Veel vogeluitwerpselen", value=False)
with o2:
    optie_hardnekkig = st.checkbox("Hardnekkig vuil", value=False)
    optie_stof = st.checkbox("Stoflaag", value=False)
with o3:
    optie_hoogtewerker = st.checkbox("Hoogtewerker nodig", value=False)
    optie_ankerpunt = st.checkbox("Mobiel ankerpunt nodig", value=False)
with o4:
    coating_opnemen = st.checkbox("Optioneel: coating tonen", value=True)

# ======================== CONFIGURATIE =====================
CONFIG = {}
CONFIG.update(COMPANY_CONFIG)
CONFIG.update({
    "minimum_tarief": minimum_tarief,
    "afstandskosten_per_km": afstandskosten_per_km,
    "uurtarief": uurtarief,
    "aantal_personen": int(aantal_personen),   # enkel voor berekening; niet zichtbaar in PDF
    "overhead_percentage": overhead_percentage,
    "btw_percentage": btw_percentage,
    "max_werkuren_per_dag": max_werkuren_per_dag,
    "opstart_afbouw_per_dag": opstart_afbouw_per_dag,
    "waterbron": "osmose" if waterbron == "osmose" else "leiding",
    "hoogtewerker_kost_per_dag": hoogtewerker_kost_per_dag,
    "mobiel_ankerpunt_kost_per_dag": mobiel_ankerpunt_kost_per_dag,
    "kosten_osmose_water_per_m3": kosten_osmose_water_per_m3,
    "paneel_oppervlakte_m2": paneel_oppervlakte_m2,
    "coating_prijs_per_5L": coating_prijs_per_5L,
    "coating_hoeveelheid_per_1000L": coating_hoeveelheid_per_1000L,
    "extra_tijd_korstmos_factor": extra_tijd_korstmos_factor,
    "korstmos_product_kostprijs": korstmos_product_kostprijs,
    "korstmos_product_dekking_m2": korstmos_product_dekking_m2,
    "extra_tijd_vogeluitwerpselen_factor": extra_tijd_vogeluitwerpselen_factor,
    "vogeluitwerpselen_product_kostprijs_per_liter": vogeluitwerpselen_product_kostprijs_per_liter,
    "verhouding_product_naar_osmose_water": int(verhouding_product_naar_osmose_water),
    "extra_tijd_hardnekkig_factor": extra_tijd_hardnekkig_factor,
    "hardnekkig_vuil_product_kostprijs_per_liter": hardnekkig_vuil_product_kostprijs_per_liter,
    "extra_tijd_stoflaag_factor": extra_tijd_stoflaag_factor,
    "snelheid_plat_ppu": int(snelheid_plat_ppu),
    "snelheid_schuin_ppu": int(snelheid_schuin_ppu),
})

def bereken_kosten_per_paneel(aantal_panelen, afstand_km, opties, dak_type="plat", config=CONFIG):
    if aantal_panelen <= 0:
        raise ValueError("Aantal panelen moet groter zijn dan 0.")
    if afstand_km < 0:
        raise ValueError("Afstand kan niet negatief zijn.")

    # Snelheid -> uren per paneel per persoon
    if dak_type.lower() == "plat":
        ppu = max(config["snelheid_plat_ppu"], 1)
    else:
        ppu = max(config["snelheid_schuin_ppu"], 1)
    base_time_per_panel = 1 / ppu

    # Vertraagfactoren
    multiplier = 1.0
    if opties.get("korstmos", False):
        multiplier *= config["extra_tijd_korstmos_factor"]
    if opties.get("vogeluitwerpselen", False):
        multiplier *= config["extra_tijd_vogeluitwerpselen_factor"]
    if opties.get("hardnekkig_vuil", False):
        multiplier *= config["extra_tijd_hardnekkig_factor"]
    if opties.get("stoflaag", False):
        multiplier *= config["extra_tijd_stoflaag_factor"]

    # Werkuren per persoon
    werkuren_per_persoon = aantal_panelen * base_time_per_panel * multiplier

    # Opstart/afbouw per dag
    init_workdays = math.ceil(werkuren_per_persoon / config["max_werkuren_per_dag"])
    werkuren_per_persoon_incl = werkuren_per_persoon + init_workdays * config["opstart_afbouw_per_dag"]
    aantal_dagen = math.ceil(werkuren_per_persoon_incl / config["max_werkuren_per_dag"])

    # Water (vuistregel)
    osmose_water_m3 = aantal_panelen / 300
    gebruikte_waterbron = config.get("waterbron", "osmose")
    osmose_kosten = osmose_water_m3 * config["kosten_osmose_water_per_m3"] if gebruikte_waterbron == "osmose" else 0

    # Arbeid + overhead
    arbeidskosten = werkuren_per_persoon_incl * config["uurtarief"] * config["aantal_personen"]
    reinigingskosten_zonder_overhead = arbeidskosten + osmose_kosten
    if opties.get("onderhoudscontract", False):
        reinigingskosten_zonder_overhead *= (1 - 0.15)

    reinigingskosten_met_overhead = reinigingskosten_zonder_overhead * (1 + config["overhead_percentage"])
    reinigingskosten_met_overhead = max(reinigingskosten_met_overhead, config["minimum_tarief"])

    # Reizen: heen/terug per dag
    reiskosten = afstand_km * config["afstandskosten_per_km"] * aantal_dagen * 2

    # Coating (info/optie)
    water_liter = aantal_panelen * 1.0
    coating_liters = (water_liter / 1000.0) * config["coating_hoeveelheid_per_1000L"]
    coating_literprijs = config["coating_prijs_per_5L"] / 5.0
    coating_prijs = coating_liters * coating_literprijs

    # Producten
    totale_oppervlakte = aantal_panelen * config["paneel_oppervlakte_m2"]

    if opties.get("korstmos", False):
        benodigde_bussen = totale_oppervlakte / config["korstmos_product_dekking_m2"]
        korstmos_kosten = config["korstmos_product_kostprijs"] * benodigde_bussen
    else:
        korstmos_kosten = 0

    if opties.get("vogeluitwerpselen", False):
        benodigde_liters_vogel = (osmose_water_m3 * 1000) / config["verhouding_product_naar_osmose_water"]
        vogel_kosten = benodigde_liters_vogel * config["vogeluitwerpselen_product_kostprijs_per_liter"]
    else:
        vogel_kosten = 0

    if opties.get("hardnekkig_vuil", False):
        benodigde_liters_hardnekkig = (osmose_water_m3 * 1000) / config["verhouding_product_naar_osmose_water"]
        hardnekkig_kosten = benodigde_liters_hardnekkig * config["hardnekkig_vuil_product_kostprijs_per_liter"]
    else:
        hardnekkig_kosten = 0

    # Veiligheid
    hoogtewerker_kosten = (config["hoogtewerker_kost_per_dag"] * aantal_dagen) if opties.get("hoogtewerker", False) else 0
    mobiel_ankerpunt_kosten = (config["mobiel_ankerpunt_kost_per_dag"] * aantal_dagen) if opties.get("mobiel_ankerpunt", False) else 0

    optionele_kosten = korstmos_kosten + vogel_kosten + hardnekkig_kosten + hoogtewerker_kosten + mobiel_ankerpunt_kosten

    totale_kosten_excl_btw = reinigingskosten_met_overhead + reiskosten + optionele_kosten
    btw = totale_kosten_excl_btw * config["btw_percentage"]
    totale_kosten_incl_btw = totale_kosten_excl_btw + btw

    # --- Extra outputvelden voor kostenverdeling/Excel ---
    prijs_per_paneel_reiniging = reinigingskosten_met_overhead / max(aantal_panelen, 1)
    werkuren_totaal = werkuren_per_persoon_incl * config["aantal_personen"]
    osmose_liters = osmose_water_m3 * 1000

    return {
        "totale_kosten_excl_btw": round(totale_kosten_excl_btw, 2),
        "totale_kosten_incl_btw": round(totale_kosten_incl_btw, 2),
        "btw": round(btw, 2),
        "btw_percentage": config["btw_percentage"],
        "reinigingskosten": round(reinigingskosten_met_overhead, 2),
        "arbeidskosten": round(arbeidskosten, 2),
        "osmose_kosten": round(osmose_kosten, 2),
        "reiskosten": round(reiskosten, 2),
        "optionele_kosten": round(optionele_kosten, 2),
        "korstmos_kosten": round(korstmos_kosten, 2),
        "vogeluitwerpselen_kosten": round(vogel_kosten, 2),
        "hardnekkig_vuil_kosten": round(hardnekkig_kosten, 2),
        "hoogtewerker_kosten": round(hoogtewerker_kosten, 2),
        "mobiel_ankerpunt_kosten": round(mobiel_ankerpunt_kosten, 2),
        "aantal_dagen": int(aantal_dagen),
        "waterbron": gebruikte_waterbron,
        "afstand_retour_per_dag": afstand_km * 2,
        "coating_liters": round(coating_liters, 2),
        "coating_prijs": round(coating_prijs, 2),

        # nieuw voor tabel & Excel
        "prijs_per_paneel_reiniging": round(prijs_per_paneel_reiniging, 2),
        "osmose_water_m3": round(osmose_water_m3, 2),
        "osmose_water_liters": round(osmose_liters, 0),
        "werkuren_per_persoon_incl": round(werkuren_per_persoon_incl, 2),
        "werkuren_totaal": round(werkuren_totaal, 2),
    }

# ===================== PDF: header alleen op pagina 1 =====================
class OffertePDF(FPDF):
    def header(self):
        # Header (logo+gegevens) ENKEL op pagina 1
        if self.page_no() != 1:
            return
        # Logo rechtsboven
        try:
            self.image('Logo.png', x=140, y=15, w=50)
            logo_bottom = 15 + 50
        except Exception:
            logo_bottom = 15
        # Bedrijfsinfo onder het logo
        self.set_xy(140, logo_bottom + 2)
        self.set_font("helvetica", size=11)
        for lijn in [
            "Solvigo (BV)",
            "Baksveld 38, 2260 Westerlo",
            "Tel.: 0471425669",
            "Btw-nr: BE 0677.778.392",
            "IBAN: BE59 0018 1682 5558",
            "www.solvigo.be",
            "cleaning@solvigo.be",
        ]:
            self.set_x(140)
            self.cell(0, 6, lijn, ln=1)
        # onderrand van de header op pagina 1
        self.header_bottom = self.get_y()

def genereer_offerte_pdf(klantnaam, klant_bedrijfsnaam, klant_adres, aantal_panelen, afstand_km, kosten, opties, dak_type):
    pdf = OffertePDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Titel linksboven (blijft hoog)
    pdf.set_xy(10, 20)
    pdf.set_font("helvetica", 'B', 22)
    pdf.cell(0, 12, "Offerte", ln=1)

    # Offertedetails links (hoog)
    pdf.set_font("helvetica", "B", 13)
    pdf.cell(0, 8, "Offertedetails", ln=1)
    pdf.set_font("helvetica", "", 10)
    details = [
        f"Offertedatum: {offertedatum:%d-%m-%Y}",
        "Offertenummer: 1",
        f"Verloopdatum: {verloopdatum:%d-%m-%Y}",
        f"Daktype: {dak_type.capitalize()}",
    ]
    for d in details:
        pdf.cell(0, 6, d, ln=1)

    # Klantinformatie (ook hoog links)
    pdf.set_font("helvetica", "B", 13)
    pdf.cell(0, 8, "Klantinformatie", ln=1)
    pdf.set_font("helvetica", "", 11)
    if klant_bedrijfsnaam.strip():
        pdf.cell(0, 6, klant_bedrijfsnaam, ln=1)
    for regel in klant_adres.split("\n"):
        if regel.strip():
            pdf.cell(0, 6, regel, ln=1)

    # — Nu pas uitlijnen met de laagste van (linkerblok, rechter header – enkel op p.1 aanwezig)
    left_bottom = pdf.get_y()
    right_bottom = getattr(pdf, "header_bottom", left_bottom)
    pdf.set_y(max(left_bottom, right_bottom) + 8)

    # Intro
    pdf.set_font("helvetica", "", 10)
    info_tekst = (
        "Wij waarderen uw keuze voor Solvigo! Uw panelen worden efficiënt gereinigd met professionele technieken. "
        "Voor extra bescherming en langdurige reinheid adviseren wij de optionele antistatische coating."
    )
    pdf.multi_cell(0, 5, info_tekst)
    pdf.ln(6)

    # Kernwaarden
    label_w, value_w = 75, 40
    def kernrij(label, value, bold=False):
        pdf.set_font("helvetica", "", 10)
        pdf.cell(label_w, 7, label, align="L")
        pdf.set_font("helvetica", "B" if bold else "", 11)
        pdf.cell(value_w, 7, value, ln=1, align="L")

    kernrij("Aantal zonnepanelen:", f"{aantal_panelen:,}".replace(",", "."), bold=True)
    kernrij("Aantal dagen:", f"{kosten['aantal_dagen']}", bold=True)
    kernrij("Waterbron:", f"{kosten['waterbron']}", bold=True)
    pdf.ln(4)

    # Rode waarschuwing
    pdf.set_font("helvetica", "B", 8)
    pdf.set_text_color(200, 0, 0)
    pdf.multi_cell(
        0,
        6,
        "Opdrachtgever voorziet een 230V 20A stopcontact en een wateraansluiting met een debiet van minimaal 8L/minuut (standaard) of hoger nabij de installatie."
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    # Kostenoverzicht
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Kostenoverzicht", ln=1)
    pdf.set_font("helvetica", "", 10)
    pdf.set_fill_color(245, 245, 245)
    pdf.set_draw_color(120, 120, 120)
    pdf.set_line_width(0.4)

    def row(hdr, qty, unit, total):
        pdf.cell(60, 8, hdr, border=1)
        pdf.cell(35, 8, qty, border=1, align="C")
        pdf.cell(38, 8, unit, border=1, align="C")
        pdf.cell(37, 8, total, border=1, align="R")
        pdf.ln(8)

    prijs_per_paneel = kosten['reinigingskosten'] / max(aantal_panelen, 1)
    pdf.cell(60, 8, "Omschrijving", border=1, align="L", fill=True)
    pdf.cell(35, 8, "Aantal/Afstand", border=1, align="C", fill=True)
    pdf.cell(38, 8, "Prijs per eenheid", border=1, align="C", fill=True)
    pdf.cell(37, 8, "Totaal", border=1, align="R", fill=True)
    pdf.ln(8)

    row("Reiniging zonnepanelen", f"{aantal_panelen} stuks", f"{prijs_per_paneel:.2f} EUR/paneel", f"{kosten['reinigingskosten']:.2f} EUR")
    row("Verplaatsingskosten", f"{kosten['aantal_dagen']} d × {kosten['afstand_retour_per_dag']} km", f"{CONFIG['afstandskosten_per_km']:.2f} EUR/km", f"{kosten['reiskosten']:.2f} EUR")

    if opties.get("korstmos", False) and kosten["korstmos_kosten"] > 0:
        row("Korstmos product", "-", "-", f"{kosten['korstmos_kosten']:.2f} EUR")
    if opties.get("vogeluitwerpselen", False) and kosten["vogeluitwerpselen_kosten"] > 0:
        row("Vogeluitwerpselen product", "-", "-", f"{kosten['vogeluitwerpselen_kosten']:.2f} EUR")
    if opties.get("hardnekkig_vuil", False) and kosten["hardnekkig_vuil_kosten"] > 0:
        row("Hardnekkig vuil product", "-", "-", f"{kosten['hardnekkig_vuil_kosten']:.2f} EUR")
    if opties.get("hoogtewerker", False) and kosten["hoogtewerker_kosten"] > 0:
        row("Hoogtewerker", f"{kosten['aantal_dagen']} d", f"{CONFIG['hoogtewerker_kost_per_dag']:.2f} EUR/d", f"{kosten['hoogtewerker_kosten']:.2f} EUR")
    if opties.get("mobiel_ankerpunt", False) and kosten["mobiel_ankerpunt_kosten"] > 0:
        row("Mobiel ankerpunt", f"{kosten['aantal_dagen']} d", f"{CONFIG['mobiel_ankerpunt_kost_per_dag']:.2f} EUR/d", f"{kosten['mobiel_ankerpunt_kosten']:.2f} EUR")

    pdf.ln(6)

    # Coating-blok
    pdf.set_draw_color(120, 120, 120)
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(170, 8, "Optioneel: Antistatische coating", border=1, align="C", fill=True)
    pdf.ln(8)
    pdf.set_font("helvetica", "", 10)
    pdf.cell(85, 8, f"Hoeveelheid: {kosten['coating_liters']:.2f} L", border=1, align="L", fill=True)
    pdf.cell(85, 8, f"Totaalprijs: {kosten['coating_prijs']:.2f} EUR", border=1, align="L", fill=True)
    pdf.ln(10)

    # Totaal
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 7, f"Bedrag excl. BTW: {kosten['totale_kosten_excl_btw']:.2f} EUR", align="R")
    pdf.ln(7)
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 7, f"BTW ({kosten['btw_percentage']*100:.0f}%): {kosten['btw']:.2f} EUR", align="R")
    pdf.ln(7)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, f"Totaal incl. BTW: {kosten['totale_kosten_incl_btw']:.2f} EUR", align="R")
    pdf.ln(10)

    # === Algemene Voorwaarden (identiek aan robot) ===
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

    # Tweede pagina zonder header
    pdf.add_page()
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Algemene Voorwaarden - Solvigo BV", ln=1)
    pdf.set_font("helvetica", "", 8)
    for par in voorwaarden.split("\n\n"):
        pdf.multi_cell(0, 4, par)
        pdf.ln(1)

    return bytes(pdf.output(dest="S"))

# =================== Berekenen ===================
opties = {
    "onderhoudscontract": onderhoudscontract,
    "korstmos": optie_korstmos,
    "vogeluitwerpselen": optie_vogel,
    "hardnekkig_vuil": optie_hardnekkig,
    "stoflaag": optie_stof,
    "hoogtewerker": optie_hoogtewerker,
    "mobiel_ankerpunt": optie_ankerpunt,
}

kosten = bereken_kosten_per_paneel(
    aantal_panelen=aantal_panelen,
    afstand_km=afstand_km,
    opties=opties,
    dak_type=dak_type,
    config=CONFIG
)

# =================== UI: kostenverdeling ===================
st.subheader("Kostenverdeling")
rows = [
    {"Omschrijving": "Aantal dagen (info)", "Bedrag (EUR)": kosten["aantal_dagen"]},
    {"Omschrijving": "Prijs per paneel (reiniging)", "Bedrag (EUR)": kosten["prijs_per_paneel_reiniging"]},
    {"Omschrijving": "Osmosewater (L)", "Bedrag (EUR)": kosten["osmose_water_liters"]},
    {"Omschrijving": "Werkuren (totaal)", "Bedrag (EUR)": kosten["werkuren_totaal"]},

    {"Omschrijving": "Arbeidskosten", "Bedrag (EUR)": kosten["arbeidskosten"]},
    {"Omschrijving": "Osmosewater-kost", "Bedrag (EUR)": kosten["osmose_kosten"]},
    {"Omschrijving": "Reiniging totaal (incl. overhead)", "Bedrag (EUR)": kosten["reinigingskosten"]},
    {"Omschrijving": "Reiskosten", "Bedrag (EUR)": kosten["reiskosten"]},
]
if opties["hoogtewerker"]:
    rows.append({"Omschrijving": "Hoogtewerker", "Bedrag (EUR)": kosten["hoogtewerker_kosten"]})
if opties["mobiel_ankerpunt"]:
    rows.append({"Omschrijving": "Mobiel ankerpunt", "Bedrag (EUR)": kosten["mobiel_ankerpunt_kosten"]})
if opties["korstmos"]:
    rows.append({"Omschrijving": "Korstmos product", "Bedrag (EUR)": kosten["korstmos_kosten"]})
if opties["vogeluitwerpselen"]:
    rows.append({"Omschrijving": "Vogeluitwerpselen product", "Bedrag (EUR)": kosten["vogeluitwerpselen_kosten"]})
if opties["hardnekkig_vuil"]:
    rows.append({"Omschrijving": "Hardnekkig vuil product", "Bedrag (EUR)": kosten["hardnekkig_vuil_kosten"]})

rows.extend([
    {"Omschrijving": "Totale kost excl. BTW", "Bedrag (EUR)": kosten["totale_kosten_excl_btw"]},
    {"Omschrijving": f"BTW ({int(kosten['btw_percentage']*100)}%)", "Bedrag (EUR)": kosten["btw"]},
    {"Omschrijving": "Totale kost incl. BTW", "Bedrag (EUR)": kosten["totale_kosten_incl_btw"]},
])
rows.append({"Omschrijving": "Optioneel: Coating (totaal)", "Bedrag (EUR)": kosten["coating_prijs"]})

kosten_df = pd.DataFrame(rows)
st.table(kosten_df)

# =================== Excel-export (xlsx) ===================
def maak_excel_bytes():
    meta = {
        'Klantnaam': klantnaam,
        'Bedrijfsnaam': klant_bedrijfsnaam,
        'Adres': klant_adres,
        'Offertedatum': offertedatum.strftime("%d-%m-%Y"),
        'Verloopdatum': verloopdatum.strftime("%d-%m-%Y"),
        'Aantal panelen': aantal_panelen,
        'Daktype': dak_type,
        'Afstand (km) enkele rit': afstand_km,

        # extra info
        'Aantal dagen': kosten["aantal_dagen"],
        'Prijs per paneel (reiniging)': kosten["prijs_per_paneel_reiniging"],
        'Osmosewater (m³)': kosten["osmose_water_m3"],
        'Osmosewater (L)': kosten["osmose_water_liters"],
        'Werkuren per persoon (incl. op/afbouw)': kosten["werkuren_per_persoon_incl"],
        'Werkuren totaal (alle personen)': kosten["werkuren_totaal"],

        'Reinigingskosten (incl. overhead)': kosten["reinigingskosten"],
        'Reiskosten': kosten["reiskosten"],
        'Optionele kosten': kosten["optionele_kosten"],
        'Totale kost excl. BTW': kosten["totale_kosten_excl_btw"],
        'BTW (%)': kosten["btw_percentage"],
        'BTW (EUR)': kosten["btw"],
        'Totale kost incl. BTW': kosten["totale_kosten_incl_btw"],
        'Waterbron': kosten["waterbron"],
        'Coating liters (info)': kosten["coating_liters"],
        'Coating totaal (EUR, optioneel)': kosten["coating_prijs"],
    }
    if opties["korstmos"]:
        meta['Korstmos product (EUR)'] = kosten["korstmos_kosten"]
    if opties["vogeluitwerpselen"]:
        meta['Vogeluitwerpselen product (EUR)'] = kosten["vogeluitwerpselen_kosten"]
    if opties["hardnekkig_vuil"]:
        meta['Hardnekkig vuil product (EUR)'] = kosten["hardnekkig_vuil_kosten"]
    if opties["hoogtewerker"]:
        meta['Hoogtewerker (EUR)'] = kosten["hoogtewerker_kosten"]
    if opties["mobiel_ankerpunt"]:
        meta['Mobiel ankerpunt (EUR)'] = kosten["mobiel_ankerpunt_kosten"]

    df_header = pd.DataFrame([meta])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_header.to_excel(writer, index=False, sheet_name="Offerte")
        kosten_df.to_excel(writer, index=False, sheet_name="Kostenverdeling")
    return output.getvalue()

# =================== PDF-export ===================
def maak_pdf_bytes():
    return genereer_offerte_pdf(
        klantnaam=klantnaam,
        klant_bedrijfsnaam=klant_bedrijfsnaam,
        klant_adres=klant_adres,
        aantal_panelen=aantal_panelen,
        afstand_km=afstand_km,
        kosten=kosten,
        opties=opties,
        dak_type=dak_type
    )

# =================== Download knoppen ===================
colD1, colD2 = st.columns(2)
with colD1:
    st.download_button(
        label="Download Excel (.xlsx)",
        data=maak_excel_bytes(),
        file_name=f"Offerte_Manueel_{klantnaam.replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
with colD2:
    st.download_button(
        label="Download PDF",
        data=maak_pdf_bytes(),
        file_name=f"Offerte_Manueel_{klantnaam.replace(' ', '_')}.pdf",
        mime="application/pdf"
    )

st.info("Tip: wijzig parameters en zie direct de nieuwe berekening. Excel wordt altijd als .xlsx aangeboden.")
