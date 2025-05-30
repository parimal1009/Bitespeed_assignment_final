# 🔮 Bitespeed Identity Reconciliation

A sophisticated customer identity linking system built for FluxKart.com that consolidates customer identities across multiple purchases using different contact information. This system helps businesses maintain a unified view of their customers even when they use different email addresses or phone numbers for different transactions.

![Test Identity Recognition](https://github.com/parimal1009/Bitespeed_assignment_final/blob/main/images/Test-identify-recognition.png?raw=true)

## 🌟 Features

- **Smart Identity Linking**: Automatically links contacts that share email addresses or phone numbers
- **Primary/Secondary Precedence**: Maintains hierarchical contact relationships based on creation time
- **Real-time Statistics**: Live dashboard showing contact distribution and system metrics
- **Interactive Testing Interface**: Beautiful web interface for testing the identity reconciliation system
- **RESTful API**: Clean API endpoints for integration with external systems
- **Data History Tracking**: Complete audit trail of all identity recognition requests

![Test Data History](https://github.com/parimal1009/Bitespeed_assignment_final/blob/main/images/Test-data-history.png?raw=true)

## 🚀 Live Demo

The application is deployed and live on Render:
- **Web Interface**: [Your Render URL]
- **API Endpoint**: `POST /identify`
- **Health Check**: `GET /health`
- **Statistics**: `GET /contacts/stats`

## 🏗️ Architecture

### Database Schema

```sql
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phoneNumber VARCHAR(50),
    email VARCHAR(255),
    linkedId INTEGER REFERENCES contacts(id),
    linkPrecedence VARCHAR(10) NOT NULL DEFAULT 'primary',
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    deletedAt DATETIME NULL
);
```

### Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Deployment**: Render
- **Styling**: Modern glassmorphism design with animated backgrounds

## 📋 Contact Linking Logic

### Rules

1. **No existing match** → Create new **primary** contact
2. **Partial match** (email OR phone exists) → Create **secondary** contact
3. **Multiple primaries found** → Convert newer primary to **secondary**
4. **Exact match** → Return existing consolidated data

### Precedence System

- **Primary Contact**: The oldest contact in a linked group
- **Secondary Contacts**: All other contacts linked to the primary
- **Linking**: Contacts are linked if they share email OR phone number

## 🔄 API Endpoints

### POST /identify

Identify and consolidate contact information.

**Request Body:**
```json
{
  "email": "mcfly@hillvalley.edu",
  "phoneNumber": "123456"
}
```

**Response (200 OK):**
```json
{
  "contact": {
    "primaryContactId": 1,
    "emails": ["doc@hillvalley.edu", "mcfly@hillvalley.edu"],
    "phoneNumbers": ["123456"],
    "secondaryContactIds": [2, 3]
  }
}
```

### GET /health

Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "service": "Bitespeed Identity Reconciliation",
  "version": "1.0.0"
}
```

### GET /contacts/stats

Get real-time contact statistics.

**Response:**
```json
{
  "total_contacts": 150,
  "primary_contacts": 75,
  "secondary_contacts": 75
}
```

### DELETE /contacts/reset

Reset the database (development only).

## 📝 Example Scenarios

### Scenario 1: New Customer
```json
// Request
{
  "email": "doc@hillvalley.edu",
  "phoneNumber": "555-0123"
}

// Response
{
  "contact": {
    "primaryContatctId": 1,
    "emails": ["doc@hillvalley.edu"],
    "phoneNumbers": ["555-0123"],
    "secondaryContactIds": []
  }
}
```

### Scenario 2: Linking by Phone
```json
// Request (same phone, different email)
{
  "email": "mcfly@hillvalley.edu",
  "phoneNumber": "555-0123"
}

// Response (linked to existing contact)
{
  "contact": {
    "primaryContatctId": 1,
    "emails": ["doc@hillvalley.edu", "mcfly@hillvalley.edu"],
    "phoneNumbers": ["555-0123"],
    "secondaryContactIds": [2]
  }
}
```

### Scenario 3: Complex Merging
```json
// When multiple contact chains need to be merged
{
  "contact": {
    "primaryContatctId": 1,
    "emails": ["doc@hillvalley.edu", "mcfly@hillvalley.edu", "marty@future.com"],
    "phoneNumbers": ["555-0123", "555-9999"],
    "secondaryContactIds": [2, 3, 4]
  }
}
```

## 🛠️ Local Development Setup

### Prerequisites

- Python 3.8+
- pip package manager

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/parimal1009/Bitespeed_assignment_final.git
cd Bitespeed_assignment_final
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install fastapi uvicorn sqlalchemy pydantic python-multipart
```

4. **Run the application**
```bash
python main.py
```

The application will be available at `http://localhost:9000`

### Project Structure

```
bitespeed-identity-reconciliation/
├── main.py                 # FastAPI application and core logic
├── static/
│   ├── index.html         # Frontend interface
│   ├── styles.css         # Modern styling with animations
│   └── script.js          # Interactive functionality
├── contacts.db            # SQLite database (auto-created)
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🚀 Deployment on Render

### Deployment Configuration

The application is configured for Render deployment with:

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python main.py`
- **Environment**: Python 3
- **Port**: Automatically detected from environment variable

### Environment Variables

```bash
PORT=9000  # Automatically set by Render
```

### Render Deployment Steps

1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Configure build and start commands
4. Deploy automatically on git push

## 🧪 Testing the System

### Using the Web Interface

1. Visit the deployed application URL
2. Use the "Test Identity Recognition" form
3. Enter email and/or phone number
4. Observe the real-time results and statistics
5. Check the "Test Data History" for audit trail

### Using cURL

```bash
# Test new contact creation
curl -X POST "https://your-render-url.com/identify" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "phoneNumber": "123456789"}'

# Test contact linking
curl -X POST "https://your-render-url.com/identify" \
  -H "Content-Type: application/json" \
  -d '{"email": "another@example.com", "phoneNumber": "123456789"}'

# Check statistics
curl "https://your-render-url.com/contacts/stats"
```

## 📊 Performance & Scalability

### Current Implementation

- **Database**: SQLite for simplicity and portability
- **Performance**: Optimized SQL queries with proper indexing
- **Scalability**: Ready for PostgreSQL upgrade for production scale

### Production Considerations

For high-traffic production environments, consider:

- Migrate to PostgreSQL or MySQL
- Implement database connection pooling
- Add Redis for caching frequently accessed contact data
- Implement rate limiting for API endpoints
- Add comprehensive logging and monitoring

## 🔒 Security Features

- **Input Validation**: All inputs validated using Pydantic models
- **SQL Injection Protection**: Using SQLAlchemy ORM with parameterized queries
- **CORS Configuration**: Properly configured for cross-origin requests
- **Error Handling**: Comprehensive error handling without data leakage

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is part of the Bitespeed technical assessment and is intended for demonstration purposes.

## 🎯 Assignment Requirements Met

✅ **Identity Reconciliation**: Automatically links contacts with shared email/phone  
✅ **Database Schema**: Proper SQLite schema with all required fields  
✅ **Primary/Secondary Logic**: Correct precedence handling  
✅ **API Endpoint**: RESTful `/identify` endpoint with proper request/response format  
✅ **Contact Consolidation**: Merges multiple contact chains correctly  
✅ **Error Handling**: Comprehensive validation and error responses  
✅ **Web Interface**: Beautiful, interactive testing interface  
✅ **Live Deployment**: Successfully deployed on Render  

