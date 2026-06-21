from flask import Flask, request, Response, jsonify
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv
import os
from datetime import date
from typing import Optional
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

supabase: Optional[Client] = None


def _required_env(*names: str) -> list[str]:
    return [name for name in names if not os.getenv(name)]


def _get_supabase() -> Client:
    global supabase
    if supabase is None:
        missing = _required_env("SUPABASE_URL", "SUPABASE_KEY")
        if missing:
            raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    return supabase

@app.after_request
def skip_ngrok_warning(response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

@app.route("/favicon.ico")
def favicon():
    return "", 204

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWIML_APP_SID = os.getenv("TWILIO_TWIML_APP_SID")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
API_KEY = os.getenv("TWILIO_API_KEY")
API_SECRET = os.getenv("TWILIO_API_SECRET")

current_session = {}

@app.route("/")
def index():
    with open(os.path.join(BASE_DIR, "index.html"), encoding="utf-8") as file:
        return file.read()

@app.route("/favicon.ico")
def favicon():
    return "", 204

@app.route("/token", methods=["GET"])
def token():
    missing = _required_env(
        "TWILIO_ACCOUNT_SID",
        "TWILIO_API_KEY",
        "TWILIO_API_SECRET",
        "TWILIO_TWIML_APP_SID",
    )
    if missing:
        return jsonify({
            "error": "Server is missing required Twilio configuration.",
            "missing": missing,
        }), 500

    access_token = AccessToken(ACCOUNT_SID, API_KEY, API_SECRET, identity="user")
    voice_grant = VoiceGrant(
        outgoing_application_sid=TWIML_APP_SID,
        incoming_allow=True
    )
    access_token.add_grant(voice_grant)
    return {"token": access_token.to_jwt()}

@app.route("/ivr-start", methods=["POST"])
def ivr_start():
    response = VoiceResponse()
    gather = Gather(num_digits=6, action="/check-pin", method="POST")
    gather.say("Welcome to Eco Awaaz. Please enter your 6 digit area PIN code.")
    response.append(gather)
    return Response(str(response), mimetype="text/xml")

@app.route("/check-pin", methods=["POST"])
def check_pin():
    pin = request.form.get("Digits")
    response = VoiceResponse()
    response.say(f"PIN {pin} registered.")
    gather = Gather(
        input="speech",
        action=f"/after-location?pin={pin}",
        method="POST",
        speech_timeout="auto",
        language="en-IN",
        hints="street, road, nagar, colony, park, society, phase, block, sector, landmark, marg, vihar, enclave,galli"
    )
    gather.say("Please say your street name or nearby landmark now.")
    response.append(gather)
    response.redirect(f"/check-pin-retry?pin={pin}")
    return Response(str(response), mimetype="text/xml")

@app.route("/check-pin-retry", methods=["POST", "GET"])
def check_pin_retry():
    pin = request.args.get("pin", "000000")
    response = VoiceResponse()
    response.say("Sorry, I could not hear you.")
    gather = Gather(
        input="speech",
        action=f"/after-location?pin={pin}",
        method="POST",
        speech_timeout="auto",
        language="en-IN",
        hints="street, road, nagar, colony, park, society, phase, block, sector, landmark, marg, vihar, enclave"
    )
    gather.say("Please say your street name or nearby landmark again.")
    response.append(gather)
    response.say("No location detected. Using unknown as your location.")
    response.redirect(f"/after-location?pin={pin}")
    return Response(str(response), mimetype="text/xml")

@app.route("/after-location", methods=["POST"])
def after_location():
    pin = request.args.get("pin")
    location_text = request.form.get("SpeechResult", "Not provided")
    confidence = request.form.get("Confidence", "0")

    current_session["pin"] = pin
    current_session["location"] = location_text
    current_session["time"] = date.today().isoformat()

    print(f"\n{'='*50}\nSESSION STARTED\nPIN: {pin}\nLocation: {location_text}\nConfidence: {confidence}\n{'='*50}")

    response = VoiceResponse()
    response.say(f"Thank you. Location noted as {location_text}.")
    gather = Gather(num_digits=1, action="/main-menu", method="POST")
    gather.say("Now select department to register complaint.")
    gather.say("Press 1 for Water.")
    gather.say("Press 2 for Electricity.")
    gather.say("Press 3 for Waste.")
    gather.say("Press 0 to repeat this menu.")
    response.append(gather)
    return Response(str(response), mimetype="text/xml")

@app.route("/main-menu", methods=["POST"])
def main_menu():
    digit = request.form.get("Digits")
    response = VoiceResponse()

    if digit == "0":
        gather = Gather(num_digits=1, action="/main-menu", method="POST")
        gather.say("Press 1 for Water.")
        gather.say("Press 2 for Electricity.")
        gather.say("Press 3 for Waste.")
        gather.say("Press 0 to repeat this menu.")
        response.append(gather)

    elif digit == "1":
        gather = Gather(num_digits=1, action="/department-options?dept=water", method="POST")
        gather.say("Water department selected.")
        gather.say("Press 1 to hear today's notifications.")
        gather.say("Press 2 to register a complaint.")
        gather.say("Press 0 to go back.")
        response.append(gather)

    elif digit == "2":
        gather = Gather(num_digits=1, action="/department-options?dept=electricity", method="POST")
        gather.say("Electricity department selected.")
        gather.say("Press 1 to hear today's notifications.")
        gather.say("Press 2 to register a complaint.")
        gather.say("Press 0 to go back.")
        response.append(gather)

    elif digit == "3":
        gather = Gather(num_digits=1, action="/department-options?dept=waste", method="POST")
        gather.say("Waste department selected.")
        gather.say("Press 1 to hear today's notifications.")
        gather.say("Press 2 to register a complaint.")
        gather.say("Press 0 to go back.")
        response.append(gather)

    return Response(str(response), mimetype="text/xml")


@app.route("/department-options", methods=["POST"])
def department_options():
    dept = request.args.get("dept")
    digit = request.form.get("Digits")
    response = VoiceResponse()

    if digit == "0":
        # Go back to main menu
        gather = Gather(num_digits=1, action="/main-menu", method="POST")
        gather.say("Press 1 for Water.")
        gather.say("Press 2 for Electricity.")
        gather.say("Press 3 for Waste.")
        response.append(gather)

    elif digit == "1":
        # Fetch today's notifications for this department
        today = date.today().isoformat()  # e.g. "2025-04-29"
        try:
            result = _get_supabase().table("resource_info") \
                .select("description") \
                .eq("resource_type", dept) \
                .gte("created_at", f"{today}T00:00:00") \
                .lte("created_at", f"{today}T23:59:59") \
                .execute()

            notifications = result.data

            if notifications:
                valid_notifs = []
                for notif in notifications:
                    cleaned = _clean_description(notif.get('description', ''))
                    if cleaned:
                        valid_notifs.append(cleaned)

                if valid_notifs:
                    response.say(f"Here are today's notifications for {dept}.")
                    for i, cleaned_desc in enumerate(valid_notifs, 1):
                        response.say(f"Notification {i}: {cleaned_desc}.")
                    response.say("End of notifications.")
                else:
                    response.say(f"There are no notifications for {dept} today.")
            else:
                response.say(f"There are no notifications for {dept} today.")

        except Exception as e:
            print(f"Error fetching notifications: {e}")
            response.say("Sorry, we could not fetch notifications at this time.")

        # After reading, go back to department options
        gather = Gather(num_digits=1, action=f"/department-options?dept={dept}", method="POST")
        gather.say("Press 1 to hear notifications again.")
        gather.say("Press 2 to register a complaint.")
        gather.say("Press 0 to go back to main menu.")
        response.append(gather)

    elif digit == "2":
        # Go to complaint sub-menu for this department
        if dept == "water":
            response.redirect("/water-menu-entry")
        elif dept == "electricity":
            response.redirect("/electricity-menu-entry")
        elif dept == "waste":
            response.redirect("/waste-menu-entry")

    return Response(str(response), mimetype="text/xml")


# ── Water complaint menu ──────────────────────────────────────────────────────

@app.route("/water-menu-entry", methods=["POST"])
def water_menu_entry():
    response = VoiceResponse()
    gather = Gather(num_digits=1, action="/water-menu", method="POST")
    gather.say("Press 1 for No water supply.")
    gather.say("Press 2 for Dirty or contaminated water.")
    gather.say("Press 3 for Less time at common tap.")
    gather.say("Press 4 for Leaking pipe.")
    gather.say("Press 5 for Low water pressure.")
    gather.say("Press 0 to repeat this menu.")
    response.append(gather)
    return Response(str(response), mimetype="text/xml")

@app.route("/water-menu", methods=["POST"])
def water_menu():
    digit = request.form.get("Digits")
    response = VoiceResponse()

    if digit == "0":
        response.redirect("/water-menu-entry")
    else:
        issues = {
            "1": "NO_SUPPLY", "2": "DIRTY_WATER",
            "3": "LOW_TAP_TIME", "4": "LEAKING_PIPE",
            "5": "LOW_PRESSURE"
        }
        issue = issues.get(digit, "UNKNOWN")
        _save_complaint("water", issue)
        response.say(f"Your complaint for {issue} has been registered. Thank you.")
        response.hangup()

    return Response(str(response), mimetype="text/xml")


# ── Electricity complaint menu ────────────────────────────────────────────────

@app.route("/electricity-menu-entry", methods=["POST"])
def electricity_menu_entry():
    response = VoiceResponse()
    gather = Gather(num_digits=1, action="/electricity-menu", method="POST")
    gather.say("Press 1 for No power supply.")
    gather.say("Press 2 for Transformer or DC box blast.")
    gather.say("Press 3 for Street light not working.")
    gather.say("Press 4 for Loose or hanging electric wire, safety danger.")
    gather.say("Press 0 to repeat this menu.")
    response.append(gather)
    return Response(str(response), mimetype="text/xml")

@app.route("/electricity-menu", methods=["POST"])
def electricity_menu():
    digit = request.form.get("Digits")
    response = VoiceResponse()

    if digit == "0":
        response.redirect("/electricity-menu-entry")
    else:
        issues = {
            "1": "NO_POWER", "2": "TRANSFORMER_BLAST",
            "3": "STREETLIGHT_OUT", "4": "LOOSE_WIRE_HAZARD"
        }
        issue = issues.get(digit, "UNKNOWN")
        _save_complaint("electricity", issue)
        response.say(f"Your complaint for {issue} has been registered. Thank you.")
        response.hangup()

    return Response(str(response), mimetype="text/xml")


# ── Waste complaint menu ──────────────────────────────────────────────────────

@app.route("/waste-menu-entry", methods=["POST"])
def waste_menu_entry():
    response = VoiceResponse()
    gather = Gather(num_digits=1, action="/waste-menu", method="POST")
    gather.say("Press 1 for Garbage not collected.")
    gather.say("Press 2 for Blocked or broken drainage.")
    gather.say("Press 3 for Garbage dumped on road.")
    gather.say("Press 4 for Bad smell or disease risk.")
    gather.say("Press 0 to repeat this menu.")
    response.append(gather)
    return Response(str(response), mimetype="text/xml")

@app.route("/waste-menu", methods=["POST"])
def waste_menu():
    digit = request.form.get("Digits")
    response = VoiceResponse()

    if digit == "0":
        response.redirect("/waste-menu-entry")
    else:
        issues = {
            "1": "NO_COLLECTION", "2": "DRAINAGE_BLOCKED",
            "3": "ILLEGAL_DUMPING", "4": "HEALTH_HAZARD_SMELL"
        }
        issue = issues.get(digit, "UNKNOWN")
        _save_complaint("waste", issue)
        response.say(f"Your complaint for {issue} has been registered. Thank you.")
        response.hangup()

    return Response(str(response), mimetype="text/xml")


# ── Helper ────────────────────────────────────────────────────────────────────

def _clean_description(desc: str) -> str:
    if not desc:
        return ""
    import re
    
    cleaned = desc
    
    # Patterns to remove (case-insensitive)
    patterns = [
        r'(?i)\b(?:collector\s+)?arrival\s+time\s+and\s+date\s*:\s*',
        r'(?i)\b(?:collector\s+)?arrival\s+time\s+and\s+date\b',
        r'(?i)\b(?:collector\s+)?arrival\s+date\s+and\s+time\s*:\s*',
        r'(?i)\b(?:collector\s+)?arrival\s+date\s+and\s+time\b',
        r'(?i)\bwater\s+supply\s+arrival\s+time\s+and\s+date\s*:\s*',
        r'(?i)\bwater\s+supply\s+arrival\s+time\s+and\s+date\b',
        r'(?i)\barrival\s+time\s+and\s+date\s*:\s*',
        r'(?i)\barrival\s+time\s+and\s+date\b',
        r'(?i)\barrival\s+time\s*:\s*',
        r'(?i)\barrival\s+time\b',
        r'(?i)\bdeparture\s+time\s*:\s*',
        r'(?i)\bdeparture\s+time\b'
    ]
    
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned)
        
    cleaned = cleaned.strip()
    if cleaned.startswith(":"):
        cleaned = cleaned[1:].strip()
        
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


def _save_complaint(resource_type: str, issue: str):
    print(f"\n{'='*50}\nNEW COMPLAINT\nDate: {date.today().isoformat()}\nPIN: {current_session.get('pin')}\nLocation: {current_session.get('location')}\nCategory: {resource_type.upper()}\nIssue: {issue}\nStatus: PENDING\n{'='*50}")
    try:
        _get_supabase().table("complaints_detail").insert({
            "postal_code": current_session.get("pin", "unknown"),
            "address": current_session.get("location", "unknown"),
            "resource_type": resource_type,
            "complaint_type": issue,
            "status": "PENDING",
            "date": date.today().isoformat()
        }).execute()
        print("Saved to Supabase successfully.")
    except Exception as e:
        print(f"Failed to save: {e}")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
