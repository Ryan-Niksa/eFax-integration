import os
import tempfile
import logging
from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from faxplus.configuration import Configuration
from faxplus.api_client import ApiClient
from faxplus.api.files_api import FilesApi
from faxplus.api.outbox_api import OutboxApi
from faxplus.rest import ApiException
from faxplus.models.payload_outbox import PayloadOutbox
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def create_cover_letter_pdf(text: str) -> str:
    """Generate a temporary PDF file with the cover letter text."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    c = canvas.Canvas(path, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica", 12)
    
    y = height - 50
    for line in text.splitlines():
        c.drawString(50, y, line)
        y -= 20
    c.save()
    return path

@app.post("/send-fax/")
async def send_fax(
    to_number: str = Form(...),
    from_number: str = Form(...),
    cover_letter: str = Form(""),
    file: UploadFile = None
):
    print("request received", to_number, from_number, cover_letter, file.filename if file else None)
    try:
        configuration = Configuration()
        configuration.host = "https://restapi.fax.plus/v3"
        configuration.access_token = os.getenv("FAXPLUS_ACCESS_TOKEN")
        if not configuration.access_token:
            return {"error": "Missing FAXPLUS_ACCESS_TOKEN in environment"}

        api_client = ApiClient(configuration)
        files_api = FilesApi(api_client)
        outbox_api = OutboxApi(api_client)

        uploaded_paths = []

        # STEP 1a: Handle cover letter → generate PDF if not empty
        if cover_letter.strip():
            cover_pdf = create_cover_letter_pdf(cover_letter)
            uploaded_cover = files_api.upload_file(user_id="self", fax_file=cover_pdf)
            uploaded_paths.append(uploaded_cover.path)

        # STEP 1b: Handle main file
        if file:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(await file.read())
                tmp.flush()
                uploaded_file = files_api.upload_file(user_id="self", fax_file=tmp.name)
                uploaded_paths.append(uploaded_file.path)

        if not uploaded_paths:
            return {"error": "No documents to send"}

        # STEP 2: Build fax payload
        payload = PayloadOutbox(
            from_number=from_number,
            to=[to_number],
            files=uploaded_paths,  # cover first, then uploaded doc
            return_ids=True,
        )

        logger.info(f"FAX REQUEST OBJECT: {payload.__dict__}")

        # STEP 3: Send fax
        response = outbox_api.send_fax(user_id="self", body=payload)
        logger.info(f"FAX RESPONSE: {response.__dict__}")

        return {
            "upload_paths": uploaded_paths,
            "fax_ids": getattr(response, "ids", {}),
            "status": getattr(response, "status", "queued")
        }

    except ApiException as e:
        logger.error(f"Fax.Plus API error: {e.body}")
        return {"error": f"Fax.Plus API error: {e.body}"}
    except Exception as e:
        logger.exception("General error")
        return {"error": str(e)}
