import streamlit as st
import qrcode
from io import BytesIO
import base64
import pandas as pd
from database import create_db_tables, get_db, add_survey_entry, update_survey_entry_with_contact, \
                     get_current_total_sum, update_total_sum, reset_total_sum, \
                     get_all_contact_entries, get_all_volume_entries
from streamlit_autorefresh import st_autorefresh
import locale # Behalten wir für den Fall, dass andere locale-Funktionen genutzt werden, aber für Formatierung nutzen wir unsere eigene.

# --- NEUER BLOCK: Alle Zahlen in europäische Zahlenformatierung setzen ---
# Dieser Block ist weiterhin wichtig für andere potenzielle locale-abhängige Funktionen.
# Aber für die Haupt-Zahlenformatierung nutzen wir jetzt unsere eigene Funktion.
try:
    locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'de_DE')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'German_Germany.1252')
        except locale.Error:
            pass # Konnte keine deutsche Locale einstellen.

# --- NEU: Benutzerdefinierte Funktion für deutsche Zahlenformatierung ---
def format_german_currency(value):
    """
    Formatiert einen Float-Wert als deutschen Währungsstring (z.B. 1.234.567,89).
    Stellt sicher, dass das Komma als Dezimaltrennzeichen und der Punkt als Tausender-Trennzeichen verwendet wird.
    """
    if value is None:
        return "N/A"
    
    # Zuerst als String mit zwei Nachkommastellen formatieren (Standardpunkt als Dezimaltrennzeichen)
    temp_str = f"{float(value):.2f}"
    
    # Teile in Ganzzahl- und Dezimalteil auf
    parts = temp_str.split('.')
    integer_part = parts[0]
    decimal_part = parts[1]

    # Tausender-Trennzeichen zum Ganzzahlteil hinzufügen
    # Nutzt String-Formatierung mit Unterstrich als Trennzeichen, dann Ersetzung durch Punkt
    formatted_integer_part = f"{int(integer_part):_}".replace("_", ".")

    # Führt Ganzzahlteil und Dezimalteil mit Komma zusammen
    return f"{formatted_integer_part},{decimal_part}"
# --- ENDE NEUE FUNKTION ---


# --- Funktion zum Laden von Bildern als Base64 ---
def get_image_base64(image_path):
    # Sicherstellen, dass die Datei existiert, bevor versucht wird, sie zu öffnen
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        st.error(f"Fehler: Bilddatei nicht gefunden unter {image_path}. Bitte Pfad prüfen.")
        return "" # Leeren String zurückgeben, um Fehler zu vermeiden

# Logo als Base64-String laden
LOGO_BASE64 = get_image_base64("images/vfb_vam_logo.png")

# Lade das Hintergrundbild für die 10%-Anzeige als Base64-String
BACKGROUND_10_PERCENT_IMG_BASE64 = get_image_base64("images/vfb_cash-trans.png")

# --- Streamlit App Konfiguration ---
st.set_page_config(
    layout="wide",
    page_title="Versicherungsvolumen Umfrage",
    initial_sidebar_state="expanded" # Sidebar initial ausklappen (wird durch Logik gesteuert)
)

# --- CSS zur Anpassung der Streamlit UI ---
hide_streamlit_ui_and_logo_css = f"""
<style>
#MainMenu {{ visibility: hidden !important; }}
footer {{ display: none !important; }}
[data-testid="stAppFooter"] {{ display: none !important; }}
[data-testid="stToolbar"] {{ visibility: hidden !important; }}
[data-testid="stHeader"] {{ visibility: hidden !important; }}
#GithubIcon {{ display: none !important; }}

/* --- CSS für das Logo in der oberen rechten Ecke --- */
#app_logo {{ /* Selektor für das Logo-Bild */
    position: absolute; /* Absolute Positionierung relativ zum nächsten positionierten Elternelement (oft body) */
    top: 10px; /* 10 Pixel Abstand vom oberen Rand */
    right: 20px; /* 20 Pixel Abstand vom rechten Rand */
    width: 450px; /* Breite des Logos (Passe dies an deine gewünschte Größe an) */
    height: auto; /* Höhe automatisch anpassen, um Proportionen zu erhalten */
    z-index: 1000; /* Stellt sicher, dass das Logo über anderen Elementen liegt */
}}

/* --- Media Query für mobile Darstellung (bis 640px Breite) --- */
@media screen and (max-width: 640px) {{
    #app_logo {{
        width: 50%; /* Kleinere Breite für mobile Geräte */
        top: 10px;   /* Weniger Abstand vom oberen Rand auf Mobilgeräten */
        right: 10px; /* Weniger Abstand vom rechten Rand auf Mobilgeräten */
    }}
}}

/* --- Für Container --- */
.st-emotion-cache-zy6yx3 {{
    width: 100%;
    padding: 2rem 1rem 10rem;
    max-width: 1680px;
    min-width: auto;
    color: #3c3c3b;
    background-color: white;
}}

/* --- Für linke Spalte --- */

.st-emotion-cache-1mwoiw6 {{
    width: calc(40% - 1rem);
    flex: 1 1 calc(40% - 1rem);
}}

/* --- Für rechte Spalte --- */

.st-emotion-cache-wt011d {{
    width: calc(60% - 1rem);
    flex: 1 1 calc(60% - 1rem);
}}

.st-emotion-cache-8atqhb {{
margin-left: 0px;
}}

/* -- Für Auto Refresh Darstellung -- */
.stAlert {{
    margin-right: 40%;
}}

/* -- Summendarstellung -- */
.st-emotion-cache-p38tq {{
    font-size: 55px;
    color: #202f58;
    font-weight: bold;
    padding-bottom: 0.25rem;
}}

.st-emotion-cache-1wivap2 {{
    font-size: 90px;
    color: #202f58;
    font-weight: bold;
    padding-bottom: 0.25rem;
    text-align: center;
    width: 60%;
}}

@media screen and (max-width: 640px) {{
    .st-emotion-cache-1wivap2  {{
      width: 100%;
    }}
}}

/* -- 10% Bereich -- */
.stExpander.st-emotion-cache-0.e1kosxz20 {{
    text-align: center;
    width: 60%;
}}

/* Diese Regel scheint nicht mehr nötig zu sein, da der Text jetzt in <div>s ist und richtig angezeigt wird. */
/* .st-emotion-cache-1wivap2 p {{
    font-size: 0px;
    color: #ffffff;
    font-weight: bold;
    padding-bottom: 0.25rem;
    text-align: center;
    width: 50%;
}} */

/* --- ANPASSUNGEN FÜR HEADLINES --- */
.st-emotion-cache-16tyu1 h1 {{
    font-size: 50px;
    font-weight: 700;
    padding: 1.25rem 0px 1rem;
}}

@media screen and (max-width: 640px) {{
    #ihr-geschaetztes-versicherungsvolumen {{
      font-size: 24px;
      font-weight: 700;
      padding: 20% 0px 1rem;
    }}
}}

@media screen and (max-width: 640px) {{
    #vielen-dank-fuer-ihre-teilnahme {{
      font-size: 24px;
      font-weight: 700;
      padding: 20% 0px 1rem;
    }}
}}

@media screen and (max-width: 640px) {{
    #sie-moechten-mehr-erfahren {{
      font-size: 20px;
    }}
}}

/* --- Für allgemeinen Text (falls noch nicht vorhanden) --- */
.st-emotion-cache-16tyu1 p {{
    color: #3c3c3b;
}}

/* --  Button Aktualisierung -- */
button.st-emotion-cache-13lcgu3 {{
    margin-left: 0px;
}}
</style>
"""

# --- NEU: HTML-Tag für das Logo erstellen ---
logo_html_tag = f'<img id="app_logo" src="data:image/png;base64,{LOGO_BASE64}">'
st.markdown(hide_streamlit_ui_and_logo_css + logo_html_tag, unsafe_allow_html=True)


# --- Initialisierung der Datenbank ---
create_db_tables() # Stellt sicher, dass die Datenbanktabellen existieren

# --- Passwort für den Admin-Bereich ---
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]


# --- Session State Initialisierung ---
if 'page' not in st.session_state:
    st.session_state.page = 'presenter_view'

if 'last_survey_entry_id' not in st.session_state:
    st.session_state.last_survey_entry_id = None

if 'logged_in_admin' not in st.session_state:
    st.session_state.logged_in_admin = False

# --- Query Parameters aus der URL lesen ---
query_params = st.query_params

# --- Seiten-Routing-Logik basierend auf Query Parameters und Session State ---
if "view" in query_params:
    st.session_state.logged_in_admin = False

    if query_params["view"] == "survey_form":
        st.session_state.page = "survey_form"
        if "entry_id" in query_params:
            try:
                st.session_state.last_survey_entry_id = int(query_params["entry_id"])
            except ValueError:
                st.session_state.last_survey_entry_id = None
    elif query_params["view"] == "thank_you":
        st.session_state.page = "thank_you"
        if "entry_id" in query_params:
            try:
                st.session_state.last_survey_entry_id = int(query_params["entry_id"])
            except ValueError:
                st.session_state.last_survey_entry_id = None
    elif query_params["view"] == "thank_you_with_contact_option":
        st.session_state.page = "thank_you_with_contact_option"
        if "entry_id" in query_params:
            try:
                st.session_state.last_survey_entry_id = int(query_params["entry_id"])
            except ValueError:
                st.session_state.last_survey_entry_id = None

elif "admin" in query_params and not st.session_state.logged_in_admin:
    st.session_state.page = 'admin_login'

elif st.session_state.page in ["survey_form", "thank_you_with_contact_option", "thank_you", "admin_login"]:
    pass

elif not st.session_state.logged_in_admin:
    st.session_state.page = 'presenter_view'


# --- Hilfsfunktion zum Generieren von QR-Codes ---
def generate_qr_code_base64(url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=14,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


# --- Sidebar für die Navigation ---
if st.session_state.logged_in_admin or \
   st.session_state.page in ['presenter_view', 'admin_login']:
    with st.sidebar:
        st.header("Navigation")

        if st.session_state.logged_in_admin:
            if st.button("Für Präsentation (Live-Summe)", key="nav_presenter"):
                st.session_state.page = 'presenter_view'
                st.rerun()
            if st.button("Admin-Bereich", key="nav_admin"):
                st.session_state.page = 'admin_view'
                st.rerun()
            st.button("Abmelden", key="nav_logout", on_click=lambda: st.session_state.update(logged_in_admin=False, page='presenter_view'))
            st.markdown("---")
        elif st.session_state.page == 'presenter_view':
            if st.button("Als Administrator anmelden", key="nav_login_from_presenter"):
                st.session_state.page = 'admin_login'
                st.rerun()
                st.stop()

        st.caption("Umfrage Link für QR Code:")
        survey_url_base = f"https://vfb-cashback.streamlit.app/?view=survey_form"
        st.code(survey_url_base)
        st.markdown("**(Bitte URL an deine Hosting-Umgebung anpassen!)**")
else:
    pass


# --- Seiten-Rendering-Logik ---

# --- Presenter View (für die Präsentation) ---
if st.session_state.page == 'presenter_view':
    st.title("📊 LIVE RECHENBEISPIEL ")
    st.write("")

    col1, col2 = st.columns([1, 2]) # Eine Spalte für QR, eine für Summe

    with col1:
        st.subheader("Umfrage-Teilnahme")
        qr_img_data = generate_qr_code_base64(survey_url_base)
        st.image(f"data:image/png;base64,{qr_img_data}", caption="")
        st.markdown(f"Alternativ: [Direkt zum Formular]({survey_url_base})")

    with col2:
        st.subheader("Live-Summe des geschätzten Versicherungsvolumens")
        total_sum_placeholder = st.empty()
        
        # Funktion zur Aktualisierung der Gesamt-Summen-Anzeige
        def update_total_sum_display():
            db_session = next(get_db())
            try:
                current_total = get_current_total_sum(db_session)
                # NEU: Formatierung mit der benutzerdefinierten Funktion
                formatted_total = format_german_currency(current_total)
                total_sum_placeholder.metric(
                    label=" ",
                    value=f"{formatted_total} €",
                    delta_color="off"
                )
            finally:
                db_session.close()

        update_total_sum_display() # Erste Anzeige der GESAMTSUMME beim Laden der Seite

        st.info("Die Gesamtsumme wird automatisch alle 10 Sekunden aktualisiert.")

        # NEU: Expander für den 10%-Cashback-Wert
        with st.expander("10% VfB Cashback Wert anzeigen", expanded=False):
            db_session = next(get_db())
            try:
                current_total = get_current_total_sum(db_session) # Hole die aktuelle Summe
                percentage_sum = current_total * 0.10
                # NEU: Formatierung mit der benutzerdefinierten Funktion
                formatted_percentage_sum = format_german_currency(percentage_sum)

                # HTML für die 10%-Anzeige mit Hintergrundbild
                ten_percent_html = f"""
                <div style="
                    background-image: url('data:image/png;base64,{BACKGROUND_10_PERCENT_IMG_BASE64}');
                    background-size: 250px;
                    background-position: center;
                    background-repeat: no-repeat;
                    height: 450px;
                    width: 100%; /* Breite des Expanders füllen */
                    display: flex;
                    flex-direction: column;
                    justify-content: top center;
                    align-items: center;
                    margin-top: 20px;
                    color: #202f58;
                    text-align: center; /* Hier muss es 'center' sein für die Gesamtbox */
                    padding: 10px;
                ">
                    <div style="font-size: 30px; font-weight: bold; margin-bottom: 5px; color: #202f58;">
                        Davon 10% VfB Cashback Wert:
                    </div>
                    <div style="font-size: 70px; font-weight: bold; color: #202f58;">
                        {formatted_percentage_sum} €
                    </div>
                </div>
                """
                st.markdown(ten_percent_html, unsafe_allow_html=True)
            finally:
                db_session.close()

        # Manueller Aktualisieren-Button für die Gesamtsumme (kann bleiben)
        if st.button("Gesamtsumme sofort aktualisieren", key="refresh_sum_manual"):
            update_total_sum_display() # Aktualisiert die Gesamtsumme sofort
            st.success("Gesamtsumme aktualisiert!")

        # Auto-Refresh nur für die GESAMTSUMME
        st_autorefresh(interval=10 * 1000, key="total_sum_auto_refresh")


# --- Public Survey Form (für den Nutzer nach dem QR-Scan) ---
elif st.session_state.page == 'survey_form':
    st.title("💸 Ihr geschätztes Versicherungsvolumen")
    st.write("Bitte geben Sie Ihren geschätzten Betrag (€) ein:")

    # Formular zum Erfassen des Volumens
    with st.form(key='survey_form'):
        volume_input = st.number_input(
            "Geschätztes Volumen in Euro (€)",
            min_value=0.0,
            value=0.0, # Startwert
            step=1000.0,
            format="%.2f",
            key="volume_input"
        )
        submit_button = st.form_submit_button("Betrag senden")

        if submit_button:
            db_session = next(get_db())
            try:
                entry_id = add_survey_entry(db_session, volume_input)
                st.session_state.last_survey_entry_id = entry_id

                # --- WICHTIG: Direkter HTML-Redirect ---
                st.success("Ihr Betrag wurde erfolgreich erfasst! Sie werden weitergeleitet...")

                # Basis-URL (anpassen, wenn gehostet!)
                base_url = "https://vfb-cashback.streamlit.app/"
                redirect_url = f"{base_url}/?view=thank_you_with_contact_option&entry_id={entry_id}"

                # Dies ist der entscheidende Befehl: Erzwingt einen Browser-Redirect
                st.markdown(f'<meta http-equiv="refresh" content="0;url={redirect_url}">', unsafe_allow_html=True)

                # Wichtig: Beende die Skriptausführung hier, da der Browser sowieso neu lädt.
                st.stop() # NEU: Dies stoppt die Streamlit-Ausführung elegant.

            except Exception as e:
                st.error(f"Ein Fehler ist aufgetreten: {e}")
                st.session_state.last_survey_entry_id = None # Im Fehlerfall ID löschen
                # Hier ist kein st.rerun() nötig, da der Fehler angezeigt wird und die Ausführung danach eh endet.
            finally:
                db_session.close() # Datenbank-Session immer schließen

            # Keinen st.rerun() hier unten, da st.stop() die Ausführung schon beendet hat.


# --- NEU: Danke-Seite mit Kontaktoption ---
elif st.session_state.page == 'thank_you_with_contact_option':
    st.title("🎉 Vielen Dank für Ihre Teilnahme!")
    st.markdown("Ihre anonyme Betrags-Schätzung wurde erfolgreich übermittelt und trägt zu unserem Live-Ergebnis bei.")
    st.markdown("---")

    # WICHTIG: Sicherstellen, dass last_survey_entry_id aus Query-Parametern kommt, falls notwendig
    # (Dieser Block sollte hier sein, falls die Seite direkt per URL mit entry_id aufgerufen wird)
    if "entry_id" in query_params and st.session_state.last_survey_entry_id is None:
        try:
            st.session_state.last_survey_entry_id = int(query_params["entry_id"])
        except ValueError:
            st.session_state.last_survey_entry_id = None # Wenn ungültig, ID löschen


    if st.session_state.last_survey_entry_id: # Nur anzeigen, wenn eine Umfrage-ID vorhanden ist
        st.subheader("📣 Sie möchten mehr erfahren?")
        st.write("Hinterlassen Sie uns gerne Ihre Kontaktdaten, um weitere unverbindliche Informationen zu dieser Aktion zu erhalten.")

        with st.form(key='contact_info_form_on_new_page'): # WICHTIG: Neuen, eindeutigen Key verwenden!
            contact_name = st.text_input("Ansprechpartner*in", key="contact_name_new_page")
            contact_company = st.text_input("Firmenname", key="contact_company_new_page")
            contact_email = st.text_input("E-Mail", key="contact_email_new_page")

            contact_submit_button = st.form_submit_button("Kontaktdaten senden")

            if contact_submit_button:
                db_session = next(get_db())
                try:
                    update_survey_entry_with_contact(
                        db_session,
                        st.session_state.last_survey_entry_id,
                        contact_name if contact_name else None,
                        contact_company if contact_company else None,
                        contact_email if contact_email else None
                    )
                    st.success("Ihre Kontaktdaten wurden erfasst. Vielen Dank!")
                    st.session_state.last_survey_entry_id = None # ID löschen

                    # --- WICHTIG: Direkter HTML-Redirect zur finalen Danke-Seite ---
                    base_url = "https://vfb-cashback.streamlit.app" # ANPASSEN, WENN GEHOSTET!
                    redirect_url = f"{base_url}/?view=thank_you" # Weiterleitung zur finalen Danke-Seite

                    st.markdown(f'<meta http-equiv="refresh" content="0;url={redirect_url}">', unsafe_allow_html=True)
                    st.stop() # Beende die Skriptausführung

                except Exception as e:
                    st.error(f"Fehler beim Speichern der Kontaktdaten: {e}")
                finally:
                    db_session.close()

    else:
        # Falls man aus irgendeinem Grund hier landet ohne last_survey_entry_id
        st.warning("Es gab ein Problem beim Abrufen Ihrer Umfrage-ID. Bitte versuchen Sie es erneut.")
        if st.button("Zurück zum Umfrageformular", key="back_to_survey_from_thankyou_error"): # Eindeutiger Key
            st.session_state.page = 'survey_form'
            st.rerun()

# --- Thank You Page (FINAL) ---
elif st.session_state.page == 'thank_you':
    st.title("✨ Vielen Dank für Ihr Interesse!")
    st.markdown("Wir melden uns in den kommenden Tagen mit weiteren Informationen zur VfB Cashback Aktion bei Ihnen.")
    st.markdown("---")
    st.info("Sie können diese Seite schließen.")


# --- Admin Login Seite (jetzt mit st.form) ---
elif st.session_state.page == 'admin_login':
    st.title("🔐 Admin Login")
    st.write("Bitte geben Sie das Administrator-Passwort ein, um fortzufahren.")

    # Der gesamte Login-Bereich wird in einem st.form gekapselt
    with st.form(key="admin_login_form"):
        password_input = st.text_input("Passwort", type="password", key="admin_password_input_form")
        login_submitted = st.form_submit_button("Anmelden") # Dies ist der neue Submit-Button

        if login_submitted:
            if password_input == ADMIN_PASSWORD:
                st.session_state.logged_in_admin = True
                st.session_state.page = 'admin_view'
                st.success("Anmeldung erfolgreich! Leite weiter zum Admin-Bereich...")
                st.rerun() # Führt einen Rerun aus, um die Seite zu wechseln
            else:
                st.error("Falsches Passwort. Bitte versuchen Sie es erneut.")


# --- Admin View (für dich) ---
elif st.session_state.page == 'admin_view':
    if st.session_state.logged_in_admin:
        st.title("⚙️ Admin-Bereich")
        st.markdown("---")

        st.subheader("Summe zurücksetzen")
        st.warning("Achtung: Dies setzt die angezeigte Live-Summe auf 0 zurück!")
        if st.button("Live-Summe zurücksetzen", key="reset_button"):
            db_session = next(get_db())
            try:
                reset_total_sum(db_session)
                st.success("Die Live-Summe wurde erfolgreich auf 0 zurückgesetzt.")
            except Exception as e:
                st.error(f"Fehler beim Zurücksetzen der Summe: {e}")
            finally:
                db_session.close()
        st.markdown("---")

        st.subheader("Gesammelte Kontaktdaten")
        db_session = next(get_db())
        try:
            contact_entries = get_all_contact_entries(db_session)
            if contact_entries:
                data = []
                for entry in contact_entries:
                    # NEU: Volumen hier formatieren
                    formatted_volume = format_german_currency(entry.volume) if entry.volume else "N/A"
                    data.append({
                        "ID": entry.id,
                        "Name": entry.contact_name,
                        "Firma": entry.contact_company,
                        "E-Mail": entry.contact_email,
                        "Volumen (verknüpft)": f"{formatted_volume} €", # Angepasster Wert
                        "Zeitpunkt": entry.timestamp.strftime("%d.%m.%Y %H:%M:%S")
                    })
                df_contacts = pd.DataFrame(data)
                st.dataframe(df_contacts, use_container_width=True)

                csv_file_contacts = df_contacts.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Kontaktdaten als CSV herunterladen",
                    data=csv_file_contacts,
                    file_name="umfrage_kontaktdaten.csv",
                    mime="text/csv",
                    key="download_contacts"
                )
            else:
                st.info("Es wurden noch keine Kontaktdaten übermittelt.")
        finally:
            db_session.close()
        st.markdown("---")

        st.subheader("Alle erfassten Volumen-Einträge")
        db_session = next(get_db())
        try:
            all_volume_entries = get_all_volume_entries(db_session)
            if all_volume_entries:
                data_all = []
                for entry in all_volume_entries:
                    # NEU: Volumen hier formatieren
                    formatted_volume_all = format_german_currency(entry.volume)
                    data_all.append({
                        "ID": entry.id,
                        "Volumen (€)": f"{formatted_volume_all}", # Angepasster Wert
                        "Name": entry.contact_name if entry.contact_name else "-",
                        "Firma": entry.contact_company if entry.contact_company else "-",
                        "E-Mail": entry.contact_email if entry.contact_email else "-",
                        "Zeitpunkt": entry.timestamp.strftime("%d.%m.%Y %H:%M:%S")
                    })
                df_all = pd.DataFrame(data_all)
                st.dataframe(df_all, use_container_width=True)

                csv_file_all = df_all.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Alle Einträge als CSV herunterladen",
                    data=csv_file_all,
                    file_name="umfrage_alle_eintraege.csv",
                    mime="text/csv",
                    key="download_all_entries"
                )
            else:
                st.info("Es wurden noch keine Volumen-Einträge erfasst.")
        finally:
            db_session.close()
    else:
        st.warning("Sie sind nicht berechtigt, diesen Bereich anzuzeigen. Bitte melden Sie sich an.")
        if st.button("Zum Admin Login", key="unauthorized_admin_login_button"):
            st.session_state.page = 'admin_login'
            st.rerun()
