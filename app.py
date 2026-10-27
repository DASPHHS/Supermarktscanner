import streamlit as st
import pandas as pd
from datetime import date
from scanner import RECIPES, STORES, calculate_recipe, read_offers

st.set_page_config(page_title="Supermarktscanner", page_icon="🛒", layout="wide")
st.title("Supermarktscanner")
st.caption("Aanbiedingen AH, Jumbo en Lidl | uitsluitend ingevoerde en datum-gevalideerde prijzen")
st.warning("Er is nog geen geautomatiseerde, geverifieerde koppeling met actuele supermarktprijzen. Upload een CSV met controleerbare aanbiedingen. Zonder CSV worden geen live aanbiedingen getoond.")
st.markdown("**Doel:** vier porties per avondmaaltijd, eiwitrijke recepten en transparante kosten. Voedingswaarden zijn nog niet onafhankelijk gevalideerd.")
with st.expander("CSV-formaat en prijsregels"):
    st.code("store,product,price_eur,quantity_g,valid_from,valid_until,source_url\nAH,broccoli,1.49,500,2026-10-26,2026-11-01,https://www.ah.nl/", language="csv")
    st.write("Prijs is per verpakking. De berekening telt hele verpakkingen en markeert ontbrekende ingrediënten. Datumvelden gebruiken JJJJ-MM-DD. Alleen aanbiedingen geldig op de geselecteerde datum worden getoond.")
uploaded = st.file_uploader("Upload actuele aanbiedingen (CSV)", type=["csv"])
selected_date = st.date_input("Geldigheidsdatum", value=date.today())
store = st.selectbox("Supermarkt", sorted(STORES))
if uploaded:
    try:
        offers = read_offers(uploaded, today=selected_date)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    current = [o for o in offers if o["store"] == store]
    st.metric("Geldige aanbiedingen", len(current))
    if current:
        st.dataframe(pd.DataFrame(current), hide_index=True, use_container_width=True)
    else:
        st.info("Geen geldige aanbiedingen voor deze supermarkt en datum.")
    results = [calculate_recipe(recipe, offers, store) for recipe in RECIPES]
    complete = [r for r in results if r["complete"]]
    if complete:
        st.subheader("Volledig berekenbare recepten")
        st.dataframe(pd.DataFrame([{"Recept": r["name"], "Totaal (€)": r["known_total_eur"],
                                   "Per portie (€)": r["known_per_serving_eur"]} for r in sorted(complete, key=lambda r: r["known_total_eur"])]),
                     hide_index=True, use_container_width=True)
    st.subheader("Recepten met ontbrekende prijzen")
    for r in results:
        if not r["complete"]:
            st.write(f"**{r['name']}**: ontbreekt: {', '.join(r['missing'])}. Bekend deel €{r['known_total_eur']:.2f}, geen volledige maaltijdprijs.")
else:
    st.info("Upload eerst een aanbiedingsbestand om prijzen en recepten te vergelijken.")
st.subheader("Snelle lunchideeën")
st.write("Kwark met fruit; volkoren wrap met kip; tonijnsalade; cottage cheese met tomaat; eiersalade; tofu-bowl; skyr met noten; kip-groentesalade; omeletwrap; linzensalade.")
st.subheader("Ontbijtideeën")
st.write("Skyr met bessen; kwark met havermout; omelet met spinazie; cottage cheese met fruit; overnight oats; roerei met tomaat; Griekse yoghurt met zaden; tofu scramble; eiwitrijke smoothie; volkoren toast met ei.")
st.caption("Deze eerste versie bevat vijf startrecepten, niet de gevraagde twintig per supermarkt. De Drive-import en betrouwbare automatische prijsbronnen zijn nog niet aangesloten.")
