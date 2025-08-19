from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Wir verwenden eine lokale SQLite-Datenbankdatei
DATABASE_URL = "sqlite:///./umfrage_data.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class SurveyEntry(Base):
    __tablename__ = "survey_entries"

    id = Column(Integer, primary_key=True, index=True)
    # Das geschätzte Volumen. Standardwert 0, wenn es leer gelassen wird (nicht in diesem Formular).
    volume = Column(Float, nullable=False, default=0.0)
    contact_name = Column(String(255), nullable=True)
    contact_company = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=datetime.now)
    # Markierung, ob es sich um einen reinen Volumen-Eintrag handelt (ohne Kontakt)
    # oder ob er Kontaktinformationen enthalten könnte.
    # Hier nicht direkt verwendet, aber nützlich für komplexere Szenarien.
    has_contact_info = Column(Boolean, default=False)

class TotalSum(Base):
    __tablename__ = "total_sum"
    id = Column(Integer, primary_key=True, index=True)
    # Die aktuelle Summe, die wir live anzeigen wollen.
    # Wir speichern diese separat, um sie leichter zurücksetzen zu können.
    current_total = Column(Float, nullable=False, default=0.0)
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# Funktion zum Erstellen der Datenbanktabellen
def create_db_tables():
    Base.metadata.create_all(bind=engine)
    # Beim ersten Start sicherstellen, dass ein Summen-Eintrag existiert
    db = SessionLocal()
    if db.query(TotalSum).count() == 0:
        db.add(TotalSum(current_total=0.0))
        db.commit()
    db.close()

# Hilfsfunktion, um eine Datenbank-Session zu bekommen und sicherzustellen, dass sie geschlossen wird
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Funktionen zur Datenbank-Interaktion
def add_survey_entry(db_session, volume):
    db_entry = SurveyEntry(volume=volume)
    db_session.add(db_entry)
    db_session.commit()
    db_session.refresh(db_entry)

# NEU: Das ist der entscheidende Teil!
    # Rufe update_total_sum auf, um das hinzugefügte Volumen zur Gesamtsumme zu addieren
    update_total_sum(db_session, volume)

    # NEU: Gib die ID des neuen Eintrags zurück
    return db_entry.id # Statt 'return db_entry'
    
def update_survey_entry_with_contact(db_session, entry_id, name, company, email):
    db_entry = db_session.query(SurveyEntry).filter(SurveyEntry.id == entry_id).first()
    if db_entry:
        db_entry.contact_name = name
        db_entry.contact_company = company
        db_entry.contact_email = email
        db_entry.has_contact_info = True # Markieren, dass Kontaktinfos vorhanden sind
        db_session.commit()
        db_session.refresh(db_entry)
    return db_entry

def get_current_total_sum(db_session):
    total_obj = db_session.query(TotalSum).first()
    return total_obj.current_total if total_obj else 0.0

def update_total_sum(db_session, new_volume):
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
    total_obj = db_session.query(TotalSum).first()
    if total_obj:
        total_obj.current_total = 0.0
        total_obj.last_updated = datetime.now()
        db_session.commit()
        db_session.refresh(total_obj)
    return 0.0

def get_all_contact_entries(db_session):
    # Holen Sie alle Einträge, die Kontaktinformationen enthalten
    return db_session.query(SurveyEntry).filter(SurveyEntry.has_contact_info == True).order_by(SurveyEntry.timestamp.desc()).all()

def get_all_volume_entries(db_session):
    # Holen Sie alle Volumen-Einträge
    return db_session.query(SurveyEntry).order_by(SurveyEntry.timestamp.desc()).all()
