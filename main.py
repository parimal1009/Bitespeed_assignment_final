from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import os

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./contacts.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    phoneNumber = Column(String, nullable=True, index=True)
    email = Column(String, nullable=True, index=True)
    linkedId = Column(Integer, nullable=True, index=True)
    linkPrecedence = Column(String, nullable=False, default="primary")
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deletedAt = Column(DateTime, nullable=True)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models
class IdentifyRequest(BaseModel):
    email: Optional[str] = Field(None, example="mcfly@hillvalley.edu")
    phoneNumber: Optional[str] = Field(None, example="123456")

class ContactResponse(BaseModel):
    primaryContatctId: int
    emails: List[str]
    phoneNumbers: List[str]
    secondaryContactIds: List[int]

class IdentifyResponse(BaseModel):
    contact: ContactResponse

# FastAPI app
app = FastAPI(
    title="Bitespeed Identity Reconciliation",
    description="Identity reconciliation service for FluxKart customers",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Core business logic
class ContactService:
    @staticmethod
    def find_contacts_by_email_or_phone(db: Session, email: str = None, phone: str = None):
        """Find all contacts that match either email or phone number"""
        if not email and not phone:
            return []
        
        # Use raw SQL for better performance with complex queries
        query = """
        SELECT * FROM contacts 
        WHERE deletedAt IS NULL AND (
            (email = :email AND :email IS NOT NULL) OR 
            (phoneNumber = :phone AND :phone IS NOT NULL)
        )
        ORDER BY createdAt ASC
        """
        
        result = db.execute(text(query), {"email": email, "phone": phone})
        return [dict(row._mapping) for row in result.fetchall()]
    
    @staticmethod
    def get_all_linked_contacts(db: Session, contacts: List[dict]):
        """Get all contacts in the same link chain"""
        if not contacts:
            return []
        
        # Find all primary contacts
        primary_ids = set()
        for contact in contacts:
            if contact['linkPrecedence'] == 'primary':
                primary_ids.add(contact['id'])
            elif contact['linkedId']:
                primary_ids.add(contact['linkedId'])
        
        if not primary_ids:
            return contacts
        
        # Get all contacts linked to these primary contacts
        primary_ids_str = ','.join(map(str, primary_ids))
        query = f"""
        SELECT * FROM contacts 
        WHERE deletedAt IS NULL AND (
            id IN ({primary_ids_str}) OR 
            linkedId IN ({primary_ids_str})
        )
        ORDER BY createdAt ASC
        """
        
        result = db.execute(text(query))
        return [dict(row._mapping) for row in result.fetchall()]
    
    @staticmethod
    def consolidate_contacts(contacts: List[dict]):
        """Consolidate contact information"""
        if not contacts:
            return None
        
        primary_contact = min(contacts, key=lambda x: x['createdAt'])
        emails = []
        phone_numbers = []
        secondary_ids = []
        
        # Add primary contact info first
        if primary_contact['email']:
            emails.append(primary_contact['email'])
        if primary_contact['phoneNumber']:
            phone_numbers.append(primary_contact['phoneNumber'])
        
        # Add secondary contact info
        for contact in contacts:
            if contact['id'] != primary_contact['id']:
                secondary_ids.append(contact['id'])
                if contact['email'] and contact['email'] not in emails:
                    emails.append(contact['email'])
                if contact['phoneNumber'] and contact['phoneNumber'] not in phone_numbers:
                    phone_numbers.append(contact['phoneNumber'])
        
        return ContactResponse(
            primaryContatctId=primary_contact['id'],
            emails=emails,
            phoneNumbers=phone_numbers,
            secondaryContactIds=secondary_ids
        )
    
    @staticmethod
    def create_contact(db: Session, email: str = None, phone: str = None, 
                      linked_id: int = None, precedence: str = "primary"):
        """Create a new contact"""
        contact = Contact(
            email=email,
            phoneNumber=phone,
            linkedId=linked_id,
            linkPrecedence=precedence
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)
        return contact
    
    @staticmethod
    def update_contact_to_secondary(db: Session, contact_id: int, primary_id: int):
        """Update a contact to be secondary"""
        db.execute(
            text("UPDATE contacts SET linkedId = :primary_id, linkPrecedence = 'secondary', updatedAt = :now WHERE id = :contact_id"),
            {"primary_id": primary_id, "contact_id": contact_id, "now": datetime.utcnow()}
        )
        db.commit()

# API endpoints
@app.post("/identify", response_model=IdentifyResponse)
async def identify_contact(request: IdentifyRequest, db: Session = Depends(get_db)):
    """
    Identify and consolidate contact information
    """
    if not request.email and not request.phoneNumber:
        raise HTTPException(status_code=400, detail="Either email or phoneNumber must be provided")
    
    # Find existing contacts
    existing_contacts = ContactService.find_contacts_by_email_or_phone(
        db, request.email, request.phoneNumber
    )
    
    if not existing_contacts:
        # Create new primary contact
        new_contact = ContactService.create_contact(
            db, request.email, request.phoneNumber
        )
        return IdentifyResponse(
            contact=ContactResponse(
                primaryContatctId=new_contact.id,
                emails=[request.email] if request.email else [],
                phoneNumbers=[request.phoneNumber] if request.phoneNumber else [],
                secondaryContactIds=[]
            )
        )
    
    # Get all linked contacts
    all_contacts = ContactService.get_all_linked_contacts(db, existing_contacts)
    
    # Check if we need to create a new secondary contact
    existing_combinations = set()
    for contact in all_contacts:
        existing_combinations.add((contact.get('email'), contact.get('phoneNumber')))
    
    request_combination = (request.email, request.phoneNumber)
    
    if request_combination not in existing_combinations:
        # Find the primary contact
        primary_contact = min(all_contacts, key=lambda x: x['createdAt'])
        
        # Handle primary contact merging
        primary_contacts = [c for c in all_contacts if c['linkPrecedence'] == 'primary']
        if len(primary_contacts) > 1:
            # Multiple primaries found, merge them
            oldest_primary = min(primary_contacts, key=lambda x: x['createdAt'])
            for contact in primary_contacts:
                if contact['id'] != oldest_primary['id']:
                    ContactService.update_contact_to_secondary(
                        db, contact['id'], oldest_primary['id']
                    )
        
        # Create new secondary contact
        ContactService.create_contact(
            db, request.email, request.phoneNumber, 
            primary_contact['id'], "secondary"
        )
        
        # Refresh all contacts
        all_contacts = ContactService.get_all_linked_contacts(db, existing_contacts)
    
    # Consolidate and return
    consolidated = ContactService.consolidate_contacts(all_contacts)
    return IdentifyResponse(contact=consolidated)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/contacts/stats")
async def get_contact_stats(db: Session = Depends(get_db)):
    """Get contact statistics"""
    total_contacts = db.execute(text("SELECT COUNT(*) as count FROM contacts WHERE deletedAt IS NULL")).fetchone()[0]
    primary_contacts = db.execute(text("SELECT COUNT(*) as count FROM contacts WHERE deletedAt IS NULL AND linkPrecedence = 'primary'")).fetchone()[0]
    secondary_contacts = db.execute(text("SELECT COUNT(*) as count FROM contacts WHERE deletedAt IS NULL AND linkPrecedence = 'secondary'")).fetchone()[0]
    
    return {
        "total_contacts": total_contacts,
        "primary_contacts": primary_contacts,
        "secondary_contacts": secondary_contacts
    }

@app.delete("/contacts/reset")
async def reset_database(db: Session = Depends(get_db)):
    """Reset the database by deleting all contacts"""
    try:
        # Delete all contacts
        db.execute(text("DELETE FROM contacts"))
        # Reset the auto-increment counter
        db.execute(text("DELETE FROM sqlite_sequence WHERE name='contacts'"))
        db.commit()
        
        return {
            "message": "Database reset successfully",
            "timestamp": datetime.utcnow(),
            "total_contacts": 0,
            "primary_contacts": 0,
            "secondary_contacts": 0
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset database: {str(e)}")

app.mount("/", StaticFiles(directory="static", html=True), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the frontend HTML file"""
    return FileResponse("static/index.html")



# Create the Vercel handler
handler = app
