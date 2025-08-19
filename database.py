# database.py
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Wir verwenden eine lokale SQLite-Datenbankdatei
DATABASE_URL = "sqlite:///./umfrage_data.db"

# Erstelle die SQLAlchemy-Engine
# 'connect_args={"check_same_thread": False}' ist wichtig für SQLite
# in einer Umgebung wie Streamlit, die Multi-Threading nutzt.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Datenbankmodelle ---

class SurveyEntry(Base):
    """
    Datenbankmodell für jeden einzelnen Umfrageeintrag.
    """
    __tablename__ = "survey_entries"

    id = Column(Integer, primary_key=True, index=True)
    # Das geschätzte Volumen. Standardwert 0, wenn es leer gelassen wird (nicht in diesem Formular).
    volume = Column(Float, nullable=False, default=0.0)
    contact_name = Column(String(255), nullable=True)
    contact_company = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    # Hinzugefügte Spalte für die Telefonnummer
    contact_phone = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=datetime.now)
    # Markierung, ob es sich um einen reinen Volumen-Eintrag handelt (ohne Kontakt)
    # oder ob er Kontaktinformationen enthalten könnte.
    has_contact_info = Column(Boolean, default=False)

class TotalSum(Base):
    """
    Datenbankmodell zur Speicherung der gesamten Volumensumme.
    Nur ein Eintrag wird hier gespeichert.
    """
    __tablename__ = "total_sum"
    id = Column(Integer, primary_key=True, index=True)
    # Die aktuelle Summe, die wir live anzeigen wollen.
    # Wir speichern diese separat, um sie leichter zurücksetzen zu können.
    current_total = Column(Float, nullable=False, default=0.0)
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# Funktion zum Erstellen der Datenbanktabellen
def create_db_tables():
    """
    Erstellt alle in Base definierten Tabellen und stellt sicher, dass
    ein initialer Eintrag in der 'total_sum'-Tabelle vorhanden ist.
    """
    Base.metadata.create_all(bind=engine)
    # Beim ersten Start sicherstellen, dass ein Summen-Eintrag existiert
    db = SessionLocal()
    try:
        if db.query(TotalSum).count() == 0:
            db.add(TotalSum(current_total=0.0))
            db.commit()
    finally:
        # Sicherstellen, dass die Session immer geschlossen wird
        db.close()

# Hilfsfunktion, um eine Datenbank-Session zu bekommen und sicherzustellen, dass sie geschlossen wird
def get_db():
    """
    Stellt eine neue SQLAlchemy-Session bereit und schließt diese
    automatisch, sobald die Funktion, die sie nutzt, abgeschlossen ist.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Funktionen zur Datenbank-Interaktion ---

def add_survey_entry(db_session, volume):
    """
    Erstellt einen neuen Umfrage-Eintrag in der Datenbank.
    Aktualisiert danach die Gesamtsumme.
    Gibt die ID des neuen Eintrags zurück.
    """
    db_entry = SurveyEntry(volume=volume)
    db_session.add(db_entry)
    db_session.commit()
    db_session.refresh(db_entry)

    # Rufe update_total_sum auf, um das hinzugefügte Volumen zur Gesamtsumme zu addieren
    update_total_sum(db_session, volume)

    # Gib die ID des neuen Eintrags zurück
    return db_entry.id
    
def update_survey_entry_with_contact(db_session, entry_id, name, company, email, phone):
    """
    Aktualisiert einen bestehenden Umfrage-Eintrag mit Kontaktdaten.
    """
    db_entry = db_session.query(SurveyEntry).filter(SurveyEntry.id == entry_id).first()
    if db_entry:
        db_entry.contact_name = name
        db_entry.contact_company = company
        db_entry.contact_email = email
        db_entry.contact_phone = phone # Hier wird der Wert korrekt zugewiesen
        db_entry.has_contact_info = True # Markieren, dass Kontaktinfos vorhanden sind
        db_session.commit()
        db_session.refresh(db_entry)
    return db_entry

def get_current_total_sum(db_session):
    """
    Ruft die aktuelle Gesamtsumme aus der Datenbank ab.
    """
    total_obj = db_session.query(TotalSum).first()
    return total_obj.current_total if total_obj else 0.0

def update_total_sum(db_session, new_volume):
    """
    Aktualisiert die Gesamtsumme in der Datenbank, indem ein neuer Betrag
    hinzugefügt wird.
    """
    total_obj = db_session.query(TotalSum).first()
    if total_obj:
        total_obj.current_total += new_volume
        total_obj.last_updated = datetime.now()
    else: # Sollte nicht passieren, da wir beim Start einen Eintrag erstellen
        db_session.add(TotalSum(current_total=new_volume))
    db_session.commit()
    db_session.refresh(total_obj)
    return total_obj.current_total

def reset_total_sum(db_session):
    """
    Setzt die gesamte Volumensumme auf null zurück.
    """
    total_obj = db_session.query(TotalSum).first()
    if total_obj:
        total_obj.current_total = 0.0
        total_obj.last_updated = datetime.now()
        db_session.commit()
        db_session.refresh(total_obj)
    return 0.0

def get_all_contact_entries(db_session):
    """
    Holt alle Einträge aus der Datenbank, die Kontaktinformationen enthalten.
    """
    return db_session.query(SurveyEntry).filter(SurveyEntry.has_contact_info == True).order_by(SurveyEntry.timestamp.desc()).all()

def get_all_volume_entries(db_session):
    """
    Holt alle Volumen-Einträge aus der Datenbank.
    """
    return db_session.query(SurveyEntry).order_by(SurveyEntry.timestamp.desc()).all()
