# 🔮 Bitespeed Identity Reconciliation

A FastAPI-based customer identity reconciliation system that consolidates customer identities across multiple purchases using different contact information.

## 🌟 Features

- **Identity Linking**: Automatically links customers using email or phone number
- **Primary/Secondary Logic**: Maintains contact hierarchy based on creation time  
- **Contact Consolidation**: Merges duplicate customer profiles intelligently
- **RESTful API**: Clean JSON API endpoints for integration
- **Interactive Frontend**: Web interface for testing and monitoring
- **Real-time Statistics**: Live metrics dashboard

## 🚀 Live Demo

**API Endpoint**: `https://your-app-name.vercel.app/identify`

**Interactive Frontend**: `https://your-app-name.vercel.app`

**API Documentation**: `https://your-app-name.vercel.app/docs`

## 📋 API Usage

### POST /identify

Identify and consolidate customer contact information.

**Request Body** (JSON):
```json
{
  "email": "mcfly@hillvalley.edu",
  "phoneNumber": "123456"
}
```

**Response** (HTTP 200):
```json
{
  "contact": {
    "primaryContatctId": 1,
    "emails": ["mcfly@hillvalley.edu", "doc@hillvalley.edu"],
    "phoneNumbers": ["123456"],
    "secondaryContactIds": [2]
  }
}
```

### Example cURL Commands

**Create new contact:**
```bash
curl -X POST "https://your-app-name.vercel.app/identify" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","phoneNumber":"1234567890"}'
```

**Link existing contacts:**
```bash
curl -X POST "https://your-app-name.vercel.app/identify" \
  -H "Content-Type: application/json" \
  -d '{"email":"another@example.com","phoneNumber":"1234567890"}'
```

## 🏗️ Database Schema

```sql
Contact {
  id: Integer (Primary Key, Auto-increment)
  phoneNumber: String (Nullable, Indexed)
  email: String (Nullable, Indexed) 
  linkedId: Integer (Foreign Key to Contact.id, Nullable)
  linkPrecedence: "primary" | "secondary"
  createdAt: DateTime
  updatedAt: DateTime
  deletedAt: DateTime (Nullable)
}
```

## 🔗 Identity Linking Logic

1. **New Contact**: No matching email/phone → Create primary contact
2. **Partial Match**: Email OR phone matches → Create secondary contact
3. **Full Match**: Exact combination exists → Return existing data
4. **Primary Merge**: Multiple primaries found → Convert newer to secondary

## 🛠️ Local Development

1. **Clone Repository**:
```bash
git clone https://github.com/yourusername/bitespeed-identity-reconciliation.git
cd bitespeed-identity-reconciliation
```

2. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

3. **Run Application**:
```bash
python main.py
```

4. **Access Locally**:
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Frontend: http://localhost:8000 (if static files present)

## 📊 Additional Endpoints

- `GET /health` - Health check
- `GET /contacts/stats` - Database statistics
- `DELETE /contacts/reset` - Reset database (development only)

## 🚀 Deployment

Deployed on Vercel with automatic CI/CD from GitHub.

**Tech Stack**:
- FastAPI (Python web framework)
- SQLAlchemy (ORM)
- SQLite (Database)
- Pydantic (Data validation)
- Vercel (Hosting platform)

## 📝 Business Rules

- Contacts are linked if they share email OR phone number
- Oldest contact becomes primary, newer ones become secondary
- All linked contacts are returned as unified identity
- System handles edge cases like multiple primaries

## 🧪 Testing

Use the interactive frontend or API documentation to test various scenarios:

1. Create new contacts with unique email/phone
2. Test linking with shared email or phone
3. Verify primary/secondary precedence
4. Check contact consolidation logic

---

**Author**: Your Name  
**Project**: Bitespeed Backend Task - Identity Reconciliation  
**Framework**: FastAPI + SQLAlchemy + Vercel