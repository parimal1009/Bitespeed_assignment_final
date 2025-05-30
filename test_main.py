import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, get_db, Base, Contact
import json
import os

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_contacts.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_contacts.db"):
        os.remove("test_contacts.db")

client = TestClient(app)

class TestIdentifyEndpoint:
    
    def test_create_new_primary_contact_email_only(self, test_db):
        """Test creating a new primary contact with email only"""
        response = client.post("/identify", json={
            "email": "marty@hillvalley.edu"
        })
        
        assert response.status_code == 200
        data = response.json()
        contact = data["contact"]
        
        assert contact["primaryContatctId"] == 1
        assert contact["emails"] == ["marty@hillvalley.edu"]
        assert contact["phoneNumbers"] == []
        assert contact["secondaryContactIds"] == []
    
    def test_create_new_primary_contact_phone_only(self, test_db):
        """Test creating a new primary contact with phone only"""
        response = client.post("/identify", json={
            "phoneNumber": "555123"
        })
        
        assert response.status_code == 200
        data = response.json()
        contact = data["contact"]
        
        assert contact["primaryContatctId"] == 1
        assert contact["emails"] == []
        assert contact["phoneNumbers"] == ["555123"]
        assert contact["secondaryContactIds"] == []
    
    def test_create_new_primary_contact_both_fields(self, test_db):
        """Test creating a new primary contact with both email and phone"""
        response = client.post("/identify", json={
            "email": "doc@hillvalley.edu",
            "phoneNumber": "555doc"
        })
        
        assert response.status_code == 200
        data = response.json()
        contact = data["contact"]
        
        assert contact["primaryContatctId"] == 1
        assert contact["emails"] == ["doc@hillvalley.edu"]
        assert contact["phoneNumbers"] == ["555doc"]
        assert contact["secondaryContactIds"] == []
    
    def test_create_secondary_contact_same_phone_new_email(self, test_db):
        """Test creating secondary contact with same phone but new email"""
        # Create primary contact
        client.post("/identify", json={
            "email": "lorraine@hillvalley.edu",
            "phoneNumber": "123456"
        })
        
        # Create secondary contact
        response = client.post("/identify", json={
            "email": "mcfly@hillvalley.edu",
            "phoneNumber": "123456"
        })
        
        assert response.status_code == 200
        data = response.json()
        contact = data["contact"]
        
        assert contact["primaryContatctId"] == 1
        assert set(contact["emails"]) == {"lorraine@hillvalley.edu", "mcfly@hillvalley.edu"}
        assert contact["phoneNumbers"] == ["123456"]
        assert len(contact["secondaryContactIds"]) == 1
    
    def test_create_secondary_contact_same_email_new_phone(self, test_db):
        """Test creating secondary contact with same email but new phone"""
        # Create primary contact
        client.post("/identify", json={
            "email": "george@hillvalley.edu",
            "phoneNumber": "919191"
        })
        
        # Create secondary contact
        response = client.post("/identify", json={
            "email": "george@hillvalley.edu",
            "phoneNumber": "717171"
        })
        
        assert response.status_code == 200
        data = response.json()
        contact = data["contact"]
        
        assert contact["primaryContatctId"] == 1
        assert contact["emails"] == ["george@hillvalley.edu"]
        assert set(contact["phoneNumbers"]) == {"919191", "717171"}
        assert len(contact["secondaryContactIds"]) == 1
    
    def test_merge_primary_contacts(self, test_db):
        """Test merging two primary contacts when they share common information"""
        # Create first primary contact
        client.post("/identify", json={
            "email": "george@hillvalley.edu",
            "phoneNumber": "919191"
        })
        
        # Create second primary contact
        client.post("/identify", json={
            "email": "biffsucks@hillvalley.edu",
            "phoneNumber": "717171"
        })
        
        # Link them with common information
        response = client.post("/identify", json={
            "email": "george@hillvalley.edu",
            "phoneNumber": "717171"
        })
        
        assert response.status_code == 200
        data = response.json()
        contact = data["contact"]
        
        assert contact["primaryContatctId"] == 1  # Oldest becomes primary
        assert set(contact["emails"]) == {"george@hillvalley.edu", "biffsucks@hillvalley.edu"}
        assert set(contact["phoneNumbers"]) == {"919191", "717171"}
        assert len(contact["secondaryContactIds"]) >= 1
    
    def test_find_existing_contact_exact_match(self, test_db):
        """Test finding existing contact with exact match"""
        # Create contact
        client.post("/identify", json={
            "email": "exact@match.com",
            "phoneNumber": "exact123"
        })
        
        # Find same contact
        response = client.post("/identify", json={
            "email": "exact@match.com",
            "phoneNumber": "exact123"
        })
        
        assert response.status_code == 200
        data = response.json()
        contact = data["contact"]
        
        assert contact["primaryContatctId"] == 1
        assert contact["emails"] == ["exact@match.com"]
        assert contact["phoneNumbers"] == ["exact123"]
        assert contact["secondaryContactIds"] == []
    
    def test_find_existing_contact_partial_match_email(self, test_db):
        """Test finding existing contact by email only"""
        # Create contact
        client.post("/identify", json={
            "email": "partial@match.com",
            "phoneNumber": "partial123"
        })
        
        # Find by email only
        response = client.post("/identify", json={
            "email": "partial@match.com"
        })
        
        assert response.status_code == 200
        data = response.json()
        contact = data["contact"]
        
        assert contact["primaryContatctId"] == 1
        assert contact["emails"] == ["partial@match.com"]
        assert contact["phoneNumbers"] == ["partial123"]
    
    def test_find_existing_contact_partial_match_phone(self, test_db):
        """Test finding existing contact by phone only"""
        # Create contact
        client.post("/identify", json={
            "email": "phone@test.com",
            "phoneNumber": "phone123"
        })
        
        # Find by phone only
        response = client.post("/identify", json={
            "phoneNumber": "phone123"
        })
        
        assert response.status_code == 200
        data = response.json()
        contact = data["contact"]
        
        assert contact["primaryContatctId"] == 1
        assert contact["emails"] == ["phone@test.com"]
        assert contact["phoneNumbers"] == ["phone123"]
    
    def test_complex_linking_scenario(self, test_db):
        """Test complex scenario with multiple linking operations"""
        # Create multiple contacts
        contacts_data = [
            {"email": "user1@test.com", "phoneNumber": "111111"},
            {"email": "user2@test.com", "phoneNumber": "222222"},
            {"email": "user3@test.com", "phoneNumber": "333333"}
        ]
        
        for contact_data in contacts_data:
            client.post("/identify", json=contact_data)
        
        # Link first two contacts
        client.post("/identify", json={
            "email": "user1@test.com",
            "phoneNumber": "222222"
        })
        
        # Link all three contacts
        response = client.post("/identify", json={
            "email": "user2@test.com",
            "phoneNumber": "333333"
        })
        
        assert response.status_code == 200
        data = response.json()
        contact = data["contact"]
        
        # All contacts should be linked
        assert len(set(contact["emails"])) == 3
        assert len(set(contact["phoneNumbers"])) == 3
        assert len(contact["secondaryContactIds"]) >= 2
    
    def test_error_no_input(self, test_db):
        """Test error when no email or phone provided"""
        response = client.post("/identify", json={})
        
        assert response.status_code == 400
        assert "Either email or phoneNumber must be provided" in response.json()["detail"]
    
    def test_error_null_values(self, test_db):
        """Test error when both values are null"""
        response = client.post("/identify", json={
            "email": None,
            "phoneNumber": None
        })
        
        assert response.status_code == 400

class TestHealthAndStats:
    
    def test_health_check(self, test_db):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_contact_stats_initial(self, test_db):
        """Test contact stats endpoint with no contacts"""
        response = client.get("/contacts/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_contacts"] == 0
        assert data["primary_contacts"] == 0
        assert data["secondary_contacts"] == 0
    
    def test_contact_stats_with_contacts(self, test_db):
        """Test contact stats after creating contacts"""
        # Create some contacts
        client.post("/identify", json={"email": "stats1@test.com"})
        client.post("/identify", json={"email": "stats2@test.com"})
        client.post("/identify", json={
            "email": "stats1@test.com",
            "phoneNumber": "stats123"
        })
        
        response = client.get("/contacts/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_contacts"] == 3
        assert data["primary_contacts"] == 2
        assert data["secondary_contacts"] == 1

class TestEdgeCases:
    
    def test_empty_string_values(self, test_db):
        """Test handling of empty string values"""
        response = client.post("/identify", json={
            "email": "",
            "phoneNumber": ""
        })
        
        # Should treat empty strings as no input
        assert response.status_code == 400
    
    def test_whitespace_handling(self, test_db):
        """Test handling of whitespace in inputs"""
        response = client.post("/identify", json={
            "email": " test@whitespace.com ",
            "phoneNumber": " 123 456 "
        })
        
        assert response.status_code == 200
        # Note: In a production system, you might want to trim whitespace
    
    def test_special_characters_in_email(self, test_db):
        """Test handling special characters in email"""
        response = client.post("/identify", json={
            "email": "test+special@domain.co.uk"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["contact"]["emails"] == ["test+special@domain.co.uk"]
    
    def test_long_phone_number(self, test_db):
        """Test handling long phone numbers"""
        response = client.post("/identify", json={
            "phoneNumber": "+1234567890123456789"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["contact"]["phoneNumbers"] == ["+1234567890123456789"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])