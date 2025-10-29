from gpiozero import MCP3008
import time
from datetime import datetime
from openai import OpenAI
from twilio.rest import Client

# ==== MACHINE IDENTIFICATION ====
MACHINE_NAME = "LabSensor-01"   # <-- change this for each Pi

# ==== OPENAI SETUP ====
client = OpenAI()

# ==== TWILIO SETUP ====
TWILIO_SID = "YOUR_TWILIO_SID"
TWILIO_AUTH_TOKEN = "YOUR_TWILIO_AUTH_TOKEN"
TWILIO_FROM = "+1XXXXXXXXXX"    # your Twilio number
TWILIO_TO = "+1YYYYYYYYYY"      # your phone number for alerts

twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

def send_sms(message):
    """Send an SMS alert using Twilio."""
    try:
        twilio_client.messages.create(
            body=message,
            from_=TWILIO_FROM,
            to=TWILIO_TO
        )
        print(f"📱 SMS sent: {message}")
    except Exception as e:
        print("Error sending SMS:", e)

# ==== SENSOR SETUP ====
gas_sensor = MCP3008(channel=0)

print(f"[{MACHINE_NAME}] Warming up sensor...")
time.sleep(60)
print(f"[{MACHINE_NAME}] Warmup complete. Establishing baseline...")

# ==== BASELINE ESTABLISHMENT ====
baseline_samples = []
for _ in range(30):
    baseline_samples.append(gas_sensor.value)
    time.sleep(1)

baseline = sum(baseline_samples) / len(baseline_samples)
print(f"[{MACHINE_NAME}] Baseline established at {baseline:.4f}")

# ==== MAIN LOOP ====
while True:
    timestamp = datetime.now().strftime("%m-%d-%Y at %H:%M.%S")
    reading = gas_sensor.value
    scaled_reading = reading * 1023
    deviation = (reading - baseline) / baseline * 100

    sensor_message = (
        f"Machine: {MACHINE_NAME}\n"
        f"Time: {timestamp}\n"
        f"Gas sensor reading (scaled): {scaled_reading:.2f}\n"
        f"Gas sensor reading (raw): {reading:.4f}\n"
        f"Deviation from baseline: {deviation:.2f}%"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": (
                    "You are an air quality monitoring assistant. "
                    "Analyze sensor data trends and estimate whether vapor or other gas events might be occurring. "
                    "Be cautious — only say 'possible vapor event detected' if readings rise significantly over baseline."
                )},
                {"role": "user", "content": sensor_message}
            ]
        )

        analysis = response.choices[0].message.content
        print("\n--- New Measurement ---")
        print(f"Machine: {MACHINE_NAME}")
        print(f"Time: {timestamp}")
        print("AI analysis:", analysis)

    except Exception as e:
        print("Error analyzing with OpenAI:", e)
        analysis = None

    if deviation > 30:
        alert_message = (
            f"⚠️ ALERT from {MACHINE_NAME} at {timestamp}: "
            f"Significant increase detected ({deviation:.2f}% over baseline)!"
        )
        print(alert_message)
        send_sms(alert_message)

    time.sleep(300)
