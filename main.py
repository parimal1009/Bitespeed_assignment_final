from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import os

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./contacts.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
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

# HTML content for the frontend (embedded for simplicity)
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bitespeed Identity Reconciliation</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #000;
            color: #fff;
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
        }

        .background {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            background: linear-gradient(45deg, #000 0%, #1a1a2e 50%, #16213e 100%);
        }

        .background::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 25% 25%, rgba(120, 119, 198, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 75% 75%, rgba(255, 103, 132, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 50% 50%, rgba(54, 207, 201, 0.2) 0%, transparent 50%);
            animation: pulse 8s ease-in-out infinite alternate;
        }

        @keyframes pulse {
            0% { opacity: 0.5; transform: scale(1); }
            100% { opacity: 0.8; transform: scale(1.1); }
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
            position: relative;
            z-index: 1;
        }

        .header {
            text-align: center;
            margin-bottom: 2rem;
            padding: 2rem 0;
        }

        .header h1 {
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 1rem;
        }

        .header p {
            font-size: 1.2rem;
            color: #b8b8b8;
            max-width: 800px;
            margin: 0 auto;
        }

        .card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }

        .form-group {
            margin-bottom: 1.5rem;
        }

        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            color: #d0d0d0;
            font-weight: 500;
        }

        .form-control {
            width: 100%;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            color: white;
            font-size: 1rem;
        }

        .form-control:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 20px rgba(102, 126, 234, 0.3);
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 2rem;
            border: none;
            border-radius: 10px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }

        .result {
            background: rgba(0, 255, 0, 0.1);
            border: 1px solid rgba(0, 255, 0, 0.3);
            border-radius: 10px;
            padding: 1.5rem;
            margin-top: 1.5rem;
            color: #a0ffa0;
        }

        .error {
            background: rgba(255, 0, 0, 0.1);
            border: 1px solid rgba(255, 0, 0, 0.3);
            border-radius: 10px;
            padding: 1.5rem;
            margin-top: 1.5rem;
            color: #ffa0a0;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 2rem 1.5rem;
            text-align: center;
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 0.5rem;
        }

        .stat-label {
            color: #b8b8b8;
            font-size: 0.95rem;
            font-weight: 500;
        }

        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: 1fr;
            }
            .header h1 {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="background"></div>
    
    <div class="container">
        <div class="header">
            <h1>🔮 Bitespeed Identity Reconciliation</h1>
            <p>Advanced customer identity linking system for FluxKart.com</p>
        </div>

        <div class="card">
            <h2>Test Identity Recognition</h2>
            <form id="identifyForm">
                <div class="form-group">
                    <label for="email">Email Address</label>
                    <input type="email" id="email" class="form-control" placeholder="mcfly@hillvalley.edu">
                </div>
                <div class="form-group">
                    <label for="phone">Phone Number</label>
                    <input type="tel" id="phone" class="form-control" placeholder="123456">
                </div>
                <button type="submit" class="btn">Identify Contact</button>
            </form>
            <div id="result" style="display: none;"></div>
        </div>

        <div class="card">
            <h2>Live System Statistics</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value" id="totalContacts">-</div>
                    <div class="stat-label">Total Contacts</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="primaryContacts">-</div>
                    <div class="stat-label">Primary Contacts</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="secondaryContacts">-</div>
                    <div class="stat-label">Secondary Contacts</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Load statistics
        async function loadStats() {
            try {
                const response = await fetch('/contacts/stats');
                const data = await response.json();
                
                document.getElementById('totalContacts').textContent = data.total_contacts;
                document.getElementById('primaryContacts').textContent = data.primary_contacts;
                document.getElementById('secondaryContacts').textContent = data.secondary_contacts;
            } catch (error) {
                console.error('Failed to load stats:', error);
            }
        }

        // Handle form submission
        document.getElementById('identifyForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const email = document.getElementById('email').value.trim();
            const phone = document.getElementById('phone').value.trim();
            const resultDiv = document.getElementById('result');
            
            if (!email && !phone) {
                showResult('Please provide either an email or phone number.', 'error');
                return;
            }
            
            try {
                const requestBody = {};
                if (email) requestBody.email = email;
                if (phone) requestBody.phoneNumber = phone;
                
                const response = await fetch('/identify', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestBody)
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showResult(JSON.stringify(data, null, 2), 'result');
                    await loadStats();
                } else {
                    showResult(`Error: ${data.detail}`, 'error');
                }
            } catch (error) {
                showResult(`Network error: ${error.message}`, 'error');
            }
        });

        function showResult(content, type) {
            const resultDiv = document.getElementById('result');
            resultDiv.className = type;
            resultDiv.innerHTML = '<pre>' + content + '</pre>';
            resultDiv.style.display = 'block';
        }

        // Initialize
        loadStats();
        setInterval(loadStats, 30000);
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the frontend HTML"""
    return HTML_CONTENT

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)