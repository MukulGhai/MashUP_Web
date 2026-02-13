from flask import Flask, render_template, request, jsonify, send_file
from yt_dlp import YoutubeDL
from pydub import AudioSegment
import os, zipfile, smtplib, json
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__, static_folder='static', static_url_path='/static')
from shutil import which

AudioSegment.converter = which("ffmpeg")
AudioSegment.ffprobe = which("ffprobe")


@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")

@app.route("/api/generate", methods=["POST"])
def generate_mashup():
    try:
        data = request.json
        singer = data.get("singer")
        videos = int(data.get("videos"))
        duration = int(data.get("duration"))
        email = data.get("email")
        send_email_flag = data.get("sendEmail", False)

        if videos <= 10 or duration <= 20:
            return jsonify({"error": "At least 11 videos and 21 seconds required"}), 400

        os.makedirs("downloads", exist_ok=True)
        os.makedirs("output", exist_ok=True)

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "quiet": True,
            "socket_timeout": None,
            "http_chunk_size": 1024 * 1024,
            "retries": 5,
            "fragment_retries": 5,
            "skip_unavailable_fragments": True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"ytsearch{videos}:{singer} songs"])

        merged = AudioSegment.empty()

        for file in os.listdir("downloads"):
            if file.endswith((".mp3", ".m4a", ".webm")):
                audio = AudioSegment.from_file(f"downloads/{file}")
                merged += audio[:duration * 1000]

        output_mp3 = "output/mashup.mp3"
        merged.export(output_mp3, format="mp3")

        # Get file size for display
        file_size = os.path.getsize(output_mp3) / (1024 * 1024)  # Size in MB

        if send_email_flag and email:
            zip_path = "output/mashup.zip"
            with zipfile.ZipFile(zip_path, "w") as zipf:
                zipf.write(output_mp3)
            send_email(email, zip_path)

        return jsonify({
            "success": True,
            "message": "Mashup generated successfully!",
            "fileSize": f"{file_size:.2f} MB",
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download")
def download_mashup():
    mashup_path = "output/mashup.mp3"
    if os.path.exists(mashup_path):
        return send_file(mashup_path, as_attachment=True, download_name="mashup.mp3")
    return "Mashup not found", 404


def send_email(to_email, zip_path):
    msg = EmailMessage()
    msg["Subject"] = "Your Mashup File"
    msg["From"] = os.getenv("EMAIL_USER")
    msg["To"] = to_email
    msg.set_content("Please find your mashup file attached.")

    with open(zip_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="zip",
            filename="mashup.zip"
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(
            os.getenv("EMAIL_USER"),
            os.getenv("EMAIL_PASS")
        )
        server.send_message(msg)

if __name__ == "__main__":
    app.run(debug=True)
