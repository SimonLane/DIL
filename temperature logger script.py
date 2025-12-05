import time
import csv
from datetime import datetime
import pytesseract
from PIL import Image
import mss

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

# Set this to the location of your Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Region of the screen showing the temperature reading
# (left, top, width, height)
REGION = {"left": 449, "top": 204, "width": 41, "height": 14}

CSV_PATH = "temperature_log.csv"
INTERVAL = 1.0    # seconds between readings


# ---------------------------------------------------------
# Helper: extract temperature from image
# ---------------------------------------------------------
def extract_temperature(img: Image.Image):
    """
    Run OCR on image using custom config optimized for numbers.
    Returns a float or None if OCR failed.
    """
    text = pytesseract.image_to_string(
        img,
        config="--psm 7 -c tessedit_char_whitelist=0123456789.-"
    )

    # Clean up OCR result
    text = text.strip().replace(" ", "").replace("°", "")
    try:
        return float(text)
    except ValueError:
        return None


# ---------------------------------------------------------
# Logging setup: create CSV if not present
# ---------------------------------------------------------
def init_csv():
    try:
        with open(CSV_PATH, "x", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "temperature_C"])
    except FileExistsError:
        pass  # already exists


# ---------------------------------------------------------
# Main loop
# ---------------------------------------------------------
def main():
    init_csv()
    print("Starting real-time temperature capture...")
    print("Press Ctrl+C to stop.\n")

    with mss.mss() as sct:
        while True:
            # Capture screen region
            screenshot = sct.grab(REGION)
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

            # OCR
            temp = extract_temperature(img)

            # Timestamp
            timestamp = datetime.now().isoformat(timespec="seconds")

            # Print to console
            print(timestamp, " → ", temp)

            # Save to CSV
            with open(CSV_PATH, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, temp])

            # Wait
            time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
