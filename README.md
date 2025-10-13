# OneRoom Health Canvas Plugin

This Canvas EHR plugin captures appointment lifecycle events specifically for the **TEST-OneRoomHealth** note type and forwards comprehensive appointment data to the OneRoom backend via secure webhooks for real-time appointment management and patient coordination.

## Features

- **Filtered Event Capture**: Only processes appointments with note type "TEST-OneRoomHealth" (code: TEST-ORH)
- **Comprehensive Data Extraction**: Captures all appointment attributes including patient, provider, and scheduling details
- **Real-time Event Monitoring**: Responds to appointment creation, updates, booking, cancellation, and rescheduling
- **Secure Webhook Integration**: Sends detailed event data to OneRoom backend with authentication
- **Patient Demographics**: Includes patient name, DOB, gender, and calculated age
- **Provider Information**: Captures assigned provider details
- **Appointment Details**: Full scheduling information including time, duration, status, location, telehealth settings

## Supported Events

The plugin responds to the following Canvas appointment events for TEST-OneRoomHealth note type only:
- `APPOINTMENT_CREATED` - New TEST-OneRoomHealth appointment created
- `APPOINTMENT_UPDATED` - TEST-OneRoomHealth appointment details modified
- `APPOINTMENT_BOOKED` - TEST-OneRoomHealth appointment booked by patient or staff
- `APPOINTMENT_CANCELLED` - TEST-OneRoomHealth appointment cancelled
- `APPOINTMENT_RESCHEDULED` - TEST-OneRoomHealth appointment date/time changed

## Configuration

### Note Type Filter
The plugin only processes appointments with:
- **Note Type Display**: "TEST-OneRoomHealth"
- **Note Type Code**: "TEST-ORH"
- **Note Type System**: "TEST-ORH"

### Required Secrets
Configure these secrets in Canvas plugin settings:

- **ONEROOM_WEBHOOK_URL**: The webhook endpoint URL for your OneRoom backend
- **ONEROOM_API_KEY**: API key for authenticating webhook calls

### Webhook Payload
The plugin sends the following comprehensive JSON payload to your webhook:

```json
{
  "event_type": "APPOINTMENT_CREATED",
  "timestamp": "2025-10-01T12:00:00.000Z",
  "source": "canvas_plugin",
  "note_type_filter": "TEST-OneRoomHealth",
  "appointment": {
    "id": "12345",
    "start_time": "2025-09-26T18:00:00Z",
    "duration_minutes": 60,
    "status": "Roomed",
    "priority": "Immediate",
    "comment": "Follow-up visit",
    "note": "Patient requires lab results review",
    "appointment_type": "Lab visit",
    "note_type": {
      "code": "TEST-ORH",
      "display": "TEST-OneRoomHealth",
      "system": "TEST-ORH"
    },
    "location": "Main Office",
    "meeting_link": "https://telehealth.example.com/123",
    "telehealth_instructions_sent": true,
    "entered_in_error": false,
    "description": "Test appointment description",
    "created_at": "2025-09-26T10:00:00Z",
    "modified_at": "2025-09-26T11:00:00Z"
  },
  "patient": {
    "id": "67890",
    "first_name": "Jill",
    "last_name": "zzTest",
    "date_of_birth": "1980-01-01",
    "gender": "female",
    "age": 45
  },
  "provider": {
    "id": "98765",
    "name": "Kurt Tamaru",
    "first_name": "Kurt",
    "last_name": "Tamaru"
  },
  "context": {
    "patient": {"id": "67890"},
    "additional_context": "..."
  }
}
```

## Installation

1. Upload the plugin to Canvas
2. Configure the required secrets (ONEROOM_WEBHOOK_URL, ONEROOM_API_KEY)
3. Enable the plugin
4. Create appointments with note type "TEST-OneRoomHealth" to trigger events

## Backend Integration

Your OneRoom backend should implement a webhook endpoint that:
- Accepts POST requests with JSON payloads
- Validates the API key in the Authorization header
- Processes TEST-OneRoomHealth appointment events for real-time updates
- Handles comprehensive appointment, patient, and provider data
- Returns appropriate HTTP status codes

## Appointment Data Structure

The plugin extracts the following appointment attributes:
- **Scheduling**: Date, time, duration, status, priority
- **Patient Info**: Name, DOB, gender, calculated age
- **Provider**: Assigned healthcare provider details
- **Location**: Practice location or telehealth settings
- **Type**: Appointment and note type classifications
- **Metadata**: Creation/modification timestamps, comments, notes
- **Telehealth**: Meeting links and instruction delivery status

## Development

### Local Setup
```bash
# Clone and setup
git clone https://github.com/OneRoomHealth/orh_canvas_plugin.git
cd orh_canvas_plugin

# Setup Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install canvas-cli

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Testing
```bash
# Validate plugin structure
canvas validate

# Upload to Canvas development environment
canvas upload --env dev

# Test with TEST-OneRoomHealth appointments
# Create test appointments in Canvas with note type "TEST-OneRoomHealth"
```

## Security

- All webhook calls use HTTPS
- API key authentication required
- Request timeouts prevent hanging connections
- Comprehensive error logging without exposing sensitive data
- Only processes specified note type for security

## Support

For issues or questions:
- Canvas Plugin Documentation: https://docs.canvasmedical.com/sdk/
- OneRoom Health Support: contact@oneroomhealth.com

### Important Note!

The CANVAS_MANIFEST.json is used when installing your plugin. Please ensure it
gets updated if you add, remove, or rename protocols.
