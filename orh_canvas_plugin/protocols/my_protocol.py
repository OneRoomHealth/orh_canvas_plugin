import json
import requests  # Available in Canvas runtime environment
from datetime import datetime
import time

from canvas_sdk.effects import Effect, EffectType
from canvas_sdk.events import EventType
from canvas_sdk.protocols import BaseProtocol
from canvas_sdk.v1.data.appointment import Appointment
from canvas_sdk.v1.data.patient import Patient
from canvas_sdk.v1.data.staff import Staff
from logger import log

# Inherit from BaseProtocol to properly get registered for events
class Protocol(BaseProtocol):
    """OneRoom Health Canvas Plugin - Responds to appointment events for TEST-OneRoomHealth note type and calls OneRoom backend webhook."""

    # Name the event types you wish to run in response to
    RESPONDS_TO = [
        EventType.Name(EventType.APPOINTMENT_CHECKED_IN),
        EventType.Name(EventType.APPOINTMENT_CREATED),
        EventType.Name(EventType.APPOINTMENT_RESTORED),
        EventType.Name(EventType.APPOINTMENT_UPDATED),
        EventType.Name(EventType.APPOINTMENT_CANCELED),
        EventType.Name(EventType.APPOINTMENT_RESCHEDULED),
        EventType.Name(EventType.APPOINTMENT_NO_SHOWED)
    ]

    NARRATIVE_STRING = "OneRoom Health: TEST-OneRoomHealth appointment event processed and sent to backend."

    def __init__(self, event, secrets, environment):
        """Initialize the protocol and log that it's loaded."""
        super().__init__(event, secrets, environment)
        log.info("🚀 OneRoom Health Canvas Plugin initialized and ready to respond to appointment events!")
        log.info(f"📋 Responding to events: {[event for event in self.RESPONDS_TO]}")

    def compute(self) -> list[Effect]:
        """This method gets called when an appointment event occurs."""
        log.info(f"✅ Plugin triggered for event: {self.event.type}")
        target_resource_type = getattr(self.event.target, 'resourceType', None) or getattr(self.event.target, 'type', None)
        log.info(f"Target resource: {target_resource_type}")
        log.info(f"Context: {self.event.context}")
        try:
            # Get appointment details
            appointment_id = self.event.target.id
            appointment = None
            
            # Try to get the appointment instance
            if hasattr(self.event.target, 'instance') and self.event.target.instance:
                appointment = self.event.target.instance
            else:
                # Query for the appointment if instance not available
                appointments = Appointment.objects.filter(id=appointment_id)
                if appointments:
                    appointment = appointments[0]
            log.info(f"Appointment Details: {appointment}")
            if appointment:
                # Log specific appointment attributes we're interested in
                log.info(f"Appointment ID: {getattr(appointment, 'id', 'N/A')}")
                log.info(f"Appointment DBID: {getattr(appointment, 'dbid', 'N/A')}")
                log.info(f"Start Time: {getattr(appointment, 'start_time', 'N/A')}")
                log.info(f"End Time: {getattr(appointment, 'end_time', 'N/A')}")
                log.info(f"Status: {getattr(appointment, 'status', 'N/A')}")
                log.info(f"Note Type ID: {getattr(appointment, 'note_type_id', 'N/A')}")
                log.info(f"Note ID: {getattr(appointment, 'note_id', 'N/A')}")
                log.info(f"Description: {getattr(appointment, 'description', 'N/A')}")
                log.info(f"Comment: {getattr(appointment, 'comment', 'N/A')}")
                try:
                    log.info(f"Patient: {getattr(appointment, 'patient', 'N/A')}")
                    log.info(f"Provider: {getattr(appointment, 'provider', 'N/A')}")
                    log.info(f"Location: {getattr(appointment, 'location', 'N/A')}")
                    log.info(f"Appointment Type: {getattr(appointment, 'appointment_type', 'N/A')}")
                    log.info(f"Note Type Name: {getattr(appointment, 'note', 'NotFound')}")

                except Exception as e:
                    log.warning(f"Error accessing appointment relationships: {str(e)}")
            
            if not appointment:
                log.error(f"Could not retrieve appointment with ID: {appointment_id}")
                return []
            
            # Check if this is a TEST-OneRoomHealth appointment
            # Based on Canvas documentation, note_type_id is an Integer field
            note_type_id = getattr(appointment, 'note_type_id', None)
            note_id = getattr(appointment, 'note_id', None)
            
            # For now, we'll check if this appointment has specific metadata or identifiers
            # that indicate it's a TEST-OneRoomHealth appointment
            is_test_orh_appointment = False

            # Check appointment type (FHIR: appointmentType.coding)
            appt_type_code = None
            appt_type_display = None
            appt_type_system = None
            try:
                if hasattr(appointment, 'appointment_type') and appointment.appointment_type:
                    appt_type = appointment.appointment_type
                    # Try common shapes
                    if hasattr(appt_type, 'code') or hasattr(appt_type, 'display') or hasattr(appt_type, 'system'):
                        appt_type_code = getattr(appt_type, 'code', None)
                        appt_type_display = getattr(appt_type, 'display', None)
                        appt_type_system = getattr(appt_type, 'system', None)
                    elif hasattr(appt_type, 'coding'):
                        coding = appt_type.coding
                        if coding:
                            c0 = coding[0]
                            appt_type_code = getattr(c0, 'code', None)
                            appt_type_display = getattr(c0, 'display', None)
                            appt_type_system = getattr(c0, 'system', None)
                # Also handle camelCase FHIR-style attribute if present
                elif hasattr(appointment, 'appointmentType') and getattr(appointment, 'appointmentType'):
                    appt_type2 = getattr(appointment, 'appointmentType')
                    coding = []
                    try:
                        coding = appt_type2.coding if hasattr(appt_type2, 'coding') else appt_type2.get('coding', [])
                    except Exception:
                        coding = []
                    if coding:
                        c0 = coding[0]
                        appt_type_code = getattr(c0, 'code', None) if hasattr(c0, 'code') else c0.get('code')
                        appt_type_display = getattr(c0, 'display', None) if hasattr(c0, 'display') else c0.get('display')
                        appt_type_system = getattr(c0, 'system', None) if hasattr(c0, 'system') else c0.get('system')
            except Exception as e:
                log.warning(f"Could not parse appointment_type: {str(e)}")

            log.info(f"appt_type_code: {appt_type_code} appt_type_display: {appt_type_display}  appt_type_system: {appt_type_system}")
            # Detect TEST-OneRoomHealth via appointment type values
            if not is_test_orh_appointment:
                if (
                    str(appt_type_display).lower() == 'test-oneroomhealth' or
                    str(appt_type_code).upper() == 'TEST-ORH' or
                    str(appt_type_system).upper() == 'TEST-ORH' or
                    note_type_id == 82  # Assuming note_type_id 82 indicates TEST-OneRoomHealth   
                ):
                    is_test_orh_appointment = True
                    log.info(f"Found TEST-OneRoomHealth via appointment_type (code={appt_type_code}, display={appt_type_display}, system={appt_type_system})")

            # FHIR extension fallback for note-id if SDK note_id missing
            if not note_id:
                try:
                    extensions = getattr(appointment, 'extension', None) or getattr(appointment, 'extensions', None)
                    if extensions:
                        for ext in extensions:
                            url = getattr(ext, 'url', None) if hasattr(ext, 'url') else (ext.get('url') if isinstance(ext, dict) else None)
                            if url == 'http://schemas.canvasmedical.com/fhir/extensions/note-id':
                                val = getattr(ext, 'valueId', None) if hasattr(ext, 'valueId') else (ext.get('valueId') if isinstance(ext, dict) else None)
                                if val:
                                    note_id = val
                                    log.info(f"Mapped note_id from FHIR extension: {note_id}")
                                    break
                except Exception as e:
                    log.warning(f"Could not parse FHIR extensions for note-id: {str(e)}")

            # Fallback meeting link from contained Endpoint if SDK field missing
            meeting_link = getattr(appointment, 'meeting_link', None)
            if not meeting_link:
                try:
                    contained = getattr(appointment, 'contained', None)
                    if contained and isinstance(contained, (list, tuple)):
                        for res in contained:
                            rtype = getattr(res, 'resourceType', None) if hasattr(res, 'resourceType') else (res.get('resourceType') if isinstance(res, dict) else None)
                            if str(rtype).lower() == 'endpoint':
                                addr = getattr(res, 'address', None) if hasattr(res, 'address') else (res.get('address') if isinstance(res, dict) else None)
                                if addr:
                                    meeting_link = addr
                                    log.info("Derived meeting_link from contained Endpoint")
                                    break
                except Exception as e:
                    log.warning(f"Could not parse contained Endpoint for meeting link: {str(e)}")
            
            # Only process appointments for TEST-OneRoomHealth
            is_test_orh_appointment = True
            if not is_test_orh_appointment:
                log.info(f"Skipping appointment {appointment_id} - not TEST-OneRoomHealth type (note_type_id: {note_type_id}, appointment_type_code: {appt_type_code}, appointment_type_display: {appt_type_display})")
                return []
            
            log.info(f"OneRoom Plugin: Processing TEST-OneRoomHealth appointment event {self.event.type}")
            log.info(f"Appointment ID: {appointment_id}")
            
            # Get patient details
            patient_data = {}
            if hasattr(appointment, 'patient') and appointment.patient:
                patient = appointment.patient
                print(f"Patient:", patient)
                patient_data = {
                    "id": str(patient.id) if hasattr(patient, 'id') else None,
                    "dbid": getattr(patient, 'dbid', None),
                    "first_name": getattr(patient, 'first_name', None),
                    "last_name": getattr(patient, 'last_name', None),
                    "date_of_birth": str(patient.date_of_birth) if hasattr(patient, 'date_of_birth') and patient.date_of_birth else None,
                    "gender": getattr(patient, 'sex', None),
                    "age": self._calculate_age(patient.date_of_birth) if hasattr(patient, 'date_of_birth') and patient.date_of_birth else None,
                    "created_at": str(patient.created) if hasattr(patient, 'created') and patient.created else None,
                    "modified_at": str(patient.modified) if hasattr(patient, 'modified') and patient.modified else None
                }
            #print(f"Patient Data:", patient_data)
            log.info(f"Patient Data: {patient_data} ")
            # Get provider details  
            provider_data = {}
            if hasattr(appointment, 'provider') and appointment.provider:
                provider = appointment.provider
                print(f"Provider:", provider)

                provider_data = {
                    "id": str(provider.id) if hasattr(provider, 'id') else None,
                    "dbid": getattr(provider, 'dbid', None),
                    "name": f"{provider.first_name} {provider.last_name}" if hasattr(provider, 'first_name') and hasattr(provider, 'last_name') else None,
                    "first_name": getattr(provider, 'first_name', None),
                    "last_name": getattr(provider, 'last_name', None),
                    "created_at": str(provider.created) if hasattr(provider, 'created') and provider.created else None,
                    "modified_at": str(provider.modified) if hasattr(provider, 'modified') and provider.modified else None
                }
            #print(f"Provider Data:", provider_data)
            log.info(f"Provider Data: {provider_data} ")
            # Build schedule_user_data from participants
            schedule_user_data = []
            try:
                participants = []
                if hasattr(appointment, 'participants') and getattr(appointment, 'participants') is not None:
                    participants = getattr(appointment, 'participants')
                elif hasattr(appointment, 'participant') and getattr(appointment, 'participant') is not None:
                    participants = getattr(appointment, 'participant')

                provider_plain_id = provider_data.get('id') if isinstance(provider_data, dict) else None

                def extract_from_actor(obj, key):
                    if obj is None:
                        return None
                    if hasattr(obj, key):
                        return getattr(obj, key)
                    if isinstance(obj, dict):
                        return obj.get(key)
                    return None

                for p in participants or []:
                    actor = extract_from_actor(p, 'actor') if not hasattr(p, 'actor') else getattr(p, 'actor')
                    reference = None
                    actor_type = None
                    if actor:
                        reference = extract_from_actor(actor, 'reference')
                        actor_type = extract_from_actor(actor, 'type')
                    # fallback if reference at top level
                    if reference is None:
                        reference = extract_from_actor(p, 'reference')
                    # Compute Id from reference (split by '/')
                    ref_id = None
                    if reference:
                        try:
                            ref_id = str(reference).split('/')[-1]
                        except Exception:
                            ref_id = str(reference)
                    # Determine role and name
                    is_provider = provider_plain_id and ref_id and str(ref_id) == str(provider_plain_id)
                    role = 'provider' if is_provider else (str(actor_type) if actor_type else 'participant')
                    name = provider_data.get('name') if is_provider else ""
                    schedule_user_data.append({
                        "Id": ref_id,
                        "name": name,
                        "role": role,
                        "email": ""
                    })
            except Exception as e:
                log.warning(f"Could not build schedule_user_data from participants: {str(e)}")
            
            log.info(f"schedule_user_data Data: {schedule_user_data} ")
            # Extract comprehensive appointment details
            start_time = str(appointment.start_time) if hasattr(appointment, 'start_time') and appointment.start_time else None
            end_time = str(appointment.end_time) if hasattr(appointment, 'end_time') and appointment.end_time else None
            duration_minutes = getattr(appointment, 'duration_minutes', None)
            
            # Format start_time to include milliseconds and Z timezone
            if start_time:
                try:
                    from datetime import datetime
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    start_time = start_dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                except Exception as e:
                    log.warning(f"Could not format start_time: {str(e)}")
            
            # Calculate end_time from start_time + duration_minutes if end_time is not available
            if not end_time and start_time and duration_minutes:
                try:
                    from datetime import datetime, timedelta
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = start_dt + timedelta(minutes=duration_minutes)
                    end_time = end_dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                    log.info(f"Start_time: {start_dt}  duration: {duration_minutes}")
                    log.info(f"Calculated end_time from start_time + duration: {end_time}")
                except Exception as e:
                    log.warning(f"Could not calculate end_time from start_time + duration: {str(e)}")
            elif end_time:
                # Format existing end_time to include milliseconds and Z timezone
                try:
                    from datetime import datetime
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    end_time = end_dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                except Exception as e:
                    log.warning(f"Could not format end_time: {str(e)}")
            
            appointment_data = {
                "id": appointment_id,
                "dbid": getattr(appointment, 'dbid', None),
                "start_time": start_time,
                "end_time": end_time,
                "duration_minutes": duration_minutes,
                "status": getattr(appointment, 'status', None),
                "comment": getattr(appointment, 'comment', None),
                "note_id": note_id,
                "note_type_id": getattr(appointment, 'note_type_id', None),
                "appointment_type": {
                    "code": appt_type_code,
                    "display": appt_type_display,
                    "system": appt_type_system
                },
                "location": self._get_location_name(appointment),
                "meeting_link": meeting_link,
                "telehealth_instructions_sent": getattr(appointment, 'telehealth_instructions_sent', None),
                "entered_in_error": str(appointment.entered_in_error) if getattr(appointment, 'entered_in_error', None) else None,
                "description": getattr(appointment, 'description', None),
                "created_at": str(appointment.created) if hasattr(appointment, 'created') and appointment.created else None,
                "modified_at": str(appointment.modified) if hasattr(appointment, 'modified') and appointment.modified else None,
                "parent_appointment_id": str(appointment.parent_appointment.id) if getattr(appointment, 'parent_appointment', None) else None,
                "appointment_rescheduled_from_id": str(appointment.appointment_rescheduled_from.id) if getattr(appointment, 'appointment_rescheduled_from', None) else None
            }
            log.info(f"Appointment Data: {appointment_data} ")
            # Add external identifiers
            try:
                external_identifiers = []
                for ext_id in appointment.external_identifiers.all():
                    external_identifiers.append({
                        "id": str(ext_id.id),
                        "system": getattr(ext_id, 'system', None),
                        "value": getattr(ext_id, 'value', None),
                        "use": getattr(ext_id, 'use', None),
                        "identifier_type": getattr(ext_id, 'identifier_type', None),
                        "issued_date": str(ext_id.issued_date) if getattr(ext_id, 'issued_date', None) else None,
                        "expiration_date": str(ext_id.expiration_date) if getattr(ext_id, 'expiration_date', None) else None
                    })
                appointment_data["external_identifiers"] = external_identifiers
            except Exception as e:
                log.warning(f"Could not extract external identifiers: {str(e)}")
                appointment_data["external_identifiers"] = []
            
            # Add metadata
            try:
                metadata = []
                for meta in appointment.metadata.all():
                    metadata.append({
                        "id": str(meta.id),
                        "key": getattr(meta, 'key', None),
                        "value": getattr(meta, 'value', None)
                    })
                appointment_data["metadata"] = metadata
            except Exception as e:
                log.warning(f"Could not extract metadata: {str(e)}")
                appointment_data["metadata"] = []
            
            # Prepare payload for OneRoom backend
            webhook_payload = {
                "event_type": str(self.event.type),
                "timestamp": datetime.now().isoformat(),
                "source": "canvas_plugin",
                "filtering": {
                    "note_type_filter": "TEST-OneRoomHealth",
                    "detection_method": "appointment_type_or_metadata_or_external_ids",
                    "note_type_id": note_type_id,
                    "note_id": note_id,
                    "appointment_type": {
                        "code": appt_type_code,
                        "display": appt_type_display,
                        "system": appt_type_system
                    }
                },
                "appointment": appointment_data,
                "patient": patient_data,
                "provider": provider_data,
                "schedule_user_data": schedule_user_data,
                "context": self.event.context
            }
            log.info(f"webhook_payload Data: {webhook_payload} ")
            # Call OneRoom backend webhook
            self._send_webhook(webhook_payload, appointment_id)
            
        except Exception as e:
            log.error(f"Error processing appointment event: {str(e)}")
            
        # Craft a payload to be returned with the effect(s)
        payload = {
            "note": {"uuid": self.event.context.get("note", {}).get("uuid")},
            "data": {"narrative": self.NARRATIVE_STRING},
        }

        # Return a log effect
        return [Effect(type=EffectType.LOG, payload=json.dumps(payload))]
    
    def _calculate_age(self, date_of_birth):
        """Calculate age from date of birth."""
        try:
            if not date_of_birth:
                return None
            today = datetime.now().date()
            if isinstance(date_of_birth, str):
                dob = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
            else:
                dob = date_of_birth
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return age
        except:
            return None
    
    def _get_location_name(self, appointment):
        """Extract location name from appointment location object."""
        try:
            if not hasattr(appointment, 'location') or not appointment.location:
                return None
                
            location = appointment.location
            
            # If location is already a string, return it
            if isinstance(location, str):
                return location
                
            # Try different possible attributes for the location name
            if hasattr(location, 'name') and location.name:
                return str(location.name)
            elif hasattr(location, 'display') and location.display:
                return str(location.display)
            elif hasattr(location, 'text') and location.text:
                return str(location.text)
            else:
                # If it's an object, try to convert to string
                location_str = str(location)
                # If it's not just the object representation, return it
                if not location_str.startswith('<') and 'object at' not in location_str:
                    return location_str
                return None
        except Exception as e:
            log.warning(f"Could not extract location name: {str(e)}")
            return None
    
    def _send_webhook(self, payload, appointment_id):
        """Send webhook to OneRoom backend."""
        try:
            webhook_url = (
                self.secrets.get('WEBHOOK_URL')
                or self.secrets.get('ONEROOM_WEBHOOK_URL', 'https://your-backend-url.com/webhook/canvas')
            )
            api_key = self.secrets.get("ONEROOM_API_KEY", "")
            secret = self.secrets.get('CANVAS_WEBHOOK_SECRET', '')

            # Always send JSON array body with RoomEventInput + HMAC signature & retries
            event_input = self._build_room_event_input(payload)
            body_str = json.dumps([event_input], separators=(',', ':'))
            signature = self._compute_signature(secret, body_str) if secret else None
            body_preview = body_str[:220]

            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'OneRoom-Canvas-Plugin/1.0'
            }
            if signature:
                headers['x-canvas-signature'] = signature
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'

            attempts = 0
            backoff = 2
            while attempts < 1:
                attempts += 1
                try:
                    resp = requests.post(
                        webhook_url,
                        headers=headers,
                        data=body_str,
                        timeout=30
                    )
                    if resp.status_code == 200:
                        log.info(f"Sent appointment {appointment_id} (attempt {attempts}) bodyPreview={body_preview}")
                        return
                    else:
                        log.error(f"Webhook HTTP {resp.status_code} attempt {attempts}: {resp.text[:200]}")
                except Exception as e:
                    log.error(f"Webhook exception attempt {attempts}: {str(e)}")
                time.sleep(backoff)
                backoff *= 2

        except Exception as e:
            # Handle all exceptions generically since Canvas sandbox restricts access to requests.exceptions
            error_msg = str(e)
            if "requests" in error_msg.lower():
                log.error(f"Error calling OneRoom webhook (network): {error_msg}")
            else:
                log.error(f"Unexpected error in OneRoom webhook call: {error_msg}")
    def _build_room_event_input(self, payload: dict) -> dict:
        """Map our payload into RoomEventInput for updateRoomEvents mutation."""
        try:
            appt = payload.get('appointment', {})
            provider = payload.get('provider', {})
            patient = payload.get('patient', {})
            sched = payload.get('schedule_user_data', [])

            # Choose identifiers (required by schema)
            appointment_id = str(appt.get('id') or '')
            provider_id = str(provider.get('id') or '')
            patient_id = str(patient.get('id') or '')

            # Required fields: roomId, eventId, userId
            # Heuristic:
            # - roomId: prefer ONEROOM_ROOM_ID from env/secrets, else appointment id (or location)
            # - eventId: appointment id
            # - userId: provider id if present, else patient id, else first participant Id
            first_participant_id = None
            for p in sched:
                pid = p.get('Id') or p.get('id')
                if pid:
                    first_participant_id = str(pid)
                    break

            configured_room_id = None
            try:
                configured_room_id = self.secrets.get('ONEROOM_ROOM_ID')
            except Exception:
                configured_room_id = None
            # Removed os.getenv fallback (sandbox disallows os); rely solely on secrets
            room_id = configured_room_id or appointment_id or (appt.get('location') or 'unknown-room')
            event_id = appointment_id
            user_id = provider_id or patient_id or (first_participant_id or 'unknown-user')
            combined_event_id = f"{room_id}_{event_id}" if room_id and event_id else str(event_id or '')

            # Map schedule users to SchUserInput (id/name/role/email)
            sch_user_list = []
            for p in sched:
                sch_user_list.append({
                    'id': str(p.get('Id') or p.get('id') or ''),
                    'name': p.get('name') or '',
                    'role': p.get('role') or '',
                    'email': p.get('email') or ''
                })

            # Prefer description, else appointment_type.display
            appt_type = appt.get('appointment_type') or {}
            event_name = appt.get('description') or appt_type.get('display') or ''

            # Assemble RoomEventInput
            event_input = {
                'id': str(combined_event_id),
                'roomId': str(room_id),
                'eventId': str(event_id),
                'userId': str(user_id),
                'type': 'event',
                'timestamp': payload.get('timestamp'),
                'startTime': appt.get('start_time'),
                'endTime': appt.get('end_time'),
                'eventStatus': appt.get('status'),
                'eventName': event_name,
                'schUserList': sch_user_list,
                # Nested originals
                'appointment': payload.get('appointment'),
                'patient': payload.get('patient'),
                'provider': payload.get('provider'),
                # Additional mapped appointment fields
                'appointmentId': appointment_id,
                'appointmentDbId': appt.get('dbid'),
                'durationMinutes': appt.get('duration_minutes'),
                'comment': appt.get('comment'),
                'noteId': appt.get('note_id'),
                'noteTypeId': appt.get('note_type_id'),
                'appointmentTypeCode': (appt.get('appointment_type') or {}).get('code'),
                'appointmentTypeDisplay': (appt.get('appointment_type') or {}).get('display'),
                'appointmentTypeSystem': (appt.get('appointment_type') or {}).get('system'),
                'location': appt.get('location'),
                'meetingLink': appt.get('meeting_link'),
                'telehealthInstructionsSent': appt.get('telehealth_instructions_sent'),
                'enteredInError': appt.get('entered_in_error'),
                'description': appt.get('description'),
                'createdAt': appt.get('created_at'),
                'modifiedAt': appt.get('modified_at'),
                'parentAppointmentId': str(appt.get('parent_appointment_id')) if appt.get('parent_appointment_id') else None,
                'rescheduledFromAppointmentId': str(appt.get('appointment_rescheduled_from_id')) if appt.get('appointment_rescheduled_from_id') else None,
                'externalIdentifiers': appt.get('external_identifiers'),
                'metadata': appt.get('metadata')
            }

            log.info(f"event_input Data: {event_input} ")
            # Remove keys with None to keep payload clean
            return {k: v for k, v in event_input.items() if v is not None}
        except Exception as e:
            log.error(f"Failed to build RoomEventInput: {str(e)}")
            return {
                'roomId': self.secrets.get('ONEROOM_ROOM_ID') or payload.get('appointment', {}).get('id', 'unknown-room'),
                'eventId': payload.get('appointment', {}).get('id', 'unknown-event'),
                'userId': payload.get('provider', {}).get('id') or 'unknown-user',
                'type': 'EVENT'
            }
    
    def _compute_signature(self, secret: str, payload: str) -> str:
        """Compute HMAC-SHA256 signature for payload using provided secret."""
        try:
            import hmac, hashlib
            return hmac.new(secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
        except Exception as e:
            log.warning(f"Failed to compute signature: {str(e)}")
            return ""
