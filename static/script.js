// Test data storage
let testDataHistory = [];

// Create floating particles
function createParticles() {
    const particleCount = 50;
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';
        particle.style.width = Math.random() * 6 + 2 + 'px';
        particle.style.height = particle.style.width;
        particle.style.animationDelay = Math.random() * 6 + 's';
        particle.style.animationDuration = (Math.random() * 3 + 3) + 's';
        document.querySelector('.background').appendChild(particle);
    }
}

// API base URL
const API_BASE = window.location.origin;

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/contacts/stats`);
        const data = await response.json();
        
        document.getElementById('totalContacts').textContent = data.total_contacts;
        document.getElementById('primaryContacts').textContent = data.primary_contacts;
        document.getElementById('secondaryContacts').textContent = data.secondary_contacts;
    } catch (error) {
        console.error('Failed to load stats:', error);
        document.getElementById('totalContacts').textContent = '0';
        document.getElementById('primaryContacts').textContent = '0';
        document.getElementById('secondaryContacts').textContent = '0';
    }
}

// Update test data display
function updateTestDataDisplay() {
    const container = document.getElementById('testDataContainer');
    
    if (testDataHistory.length === 0) {
        container.innerHTML = '<div class="no-data">No test data available yet. Use the test form above to generate data.</div>';
        return;
    }

    const tableHTML = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Email</th>
                    <th>Phone Number</th>
                    <th>Status</th>
                    <th>Timestamp</th>
                </tr>
            </thead>
            <tbody>
                ${testDataHistory.map((entry, index) => `
                    <tr>
                        <td>${index + 1}</td>
                        <td>${entry.email || '-'}</td>
                        <td>${entry.phoneNumber || '-'}</td>
                        <td><span style="color: ${entry.success ? '#a0ffa0' : '#ffa0a0'}">${entry.success ? 'Success' : 'Error'}</span></td>
                        <td>${entry.timestamp}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = tableHTML;
}

// Add entry to test data history
function addTestDataEntry(email, phoneNumber, success) {
    const entry = {
        email: email || null,
        phoneNumber: phoneNumber || null,
        success: success,
        timestamp: new Date().toLocaleString()
    };
    
    testDataHistory.unshift(entry); // Add to beginning of array
    
    // Keep only last 20 entries
    if (testDataHistory.length > 20) {
        testDataHistory = testDataHistory.slice(0, 20);
    }
    
    updateTestDataDisplay();
}

// Handle form submission
document.getElementById('identifyForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('email').value.trim();
    const phone = document.getElementById('phone').value.trim();
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.getElementById('btnText');
    const resultDiv = document.getElementById('result');
    
    // Validate input
    if (!email && !phone) {
        showResult('Please provide either an email or phone number to test the system.', 'error');
        return;
    }
    
    // Show loading state
    submitBtn.disabled = true;
    btnText.innerHTML = '<span class="loading"></span>Processing Identity...';
    resultDiv.style.display = 'none';
    
    try {
        const requestBody = {};
        if (email) requestBody.email = email;
        if (phone) requestBody.phoneNumber = phone;
        
        const response = await fetch(`${API_BASE}/identify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showResult(formatContactResult(data), 'result');
            addTestDataEntry(email, phone, true);
            await loadStats(); // Refresh stats
        } else {
            showResult(`Error: ${data.detail || 'Unknown error occurred'}`, 'error');
            addTestDataEntry(email, phone, false);
        }
    } catch (error) {
        showResult(`Network error: ${error.message}`, 'error');
        addTestDataEntry(email, phone, false);
    } finally {
        // Reset button state
        submitBtn.disabled = false;
        btnText.textContent = 'Identify Contact';
    }
});

// Show result
function showResult(content, type) {
    const resultDiv = document.getElementById('result');
    resultDiv.className = type;
    resultDiv.innerHTML = content;
    resultDiv.style.display = 'block';
    
    // Scroll to result
    resultDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Format contact result
function formatContactResult(data) {
    const contact = data.contact;
    
    return `
        <div class="result-content">
            <div class="result-left">
                <h3>✅ Contact Identified Successfully!</h3>
                <div class="json-viewer">${JSON.stringify(data, null, 2)}</div>
            </div>
            <div class="result-right">
                <div class="contact-summary">
                    <strong>📊 Contact Summary:</strong><br>
                    • Primary Contact ID: <strong>${contact.primaryContatctId}</strong><br>
                    • Total Emails: <strong>${contact.emails.length}</strong> (${contact.emails.join(', ')})<br>
                    • Total Phone Numbers: <strong>${contact.phoneNumbers.length}</strong> (${contact.phoneNumbers.join(', ')})<br>
                    • Secondary Contacts: <strong>${contact.secondaryContactIds.length}</strong> ${contact.secondaryContactIds.length > 0 ? `(IDs: ${contact.secondaryContactIds.join(', ')})` : ''}
                </div>
            </div>
        </div>
    `;
}

// Initialize the page
document.addEventListener('DOMContentLoaded', () => {
    createParticles();
    loadStats();
    updateTestDataDisplay();
});

// Auto-refresh stats every 30 seconds
setInterval(loadStats, 30000);