import tempfile
import logging
from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from faxplus.configuration import Configuration
from faxplus.api_client import ApiClient
from faxplus.api.files_api import FilesApi
from faxplus.api.outbox_api import OutboxApi
from faxplus.rest import ApiException
from faxplus.models.outbox_comment import OutboxComment
from faxplus.models.payload_outbox import PayloadOutbox
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/send-fax/")
async def send_fax(
    to_number: str = Form(...),
    from_number: str = Form(...),   # ✅ must come from frontend
    cover_letter: str = Form(""),
    file: UploadFile = None
):
    print("request received", to_number, from_number, cover_letter, file.filename)
    try:
        # Configure Fax.Plus client
        configuration = Configuration()
        configuration.host = "https://restapi.fax.plus/v3"
        configuration.access_token = "alohi_pat_NDGRR6lWT1xtNv8XvJirEf_oABCVaO9ezACqo6yyLgAOLMVnefll5q2PzHMebjtsLG6nHxgY7mDxZTy3SG" 

        api_client = ApiClient(configuration)
        files_api = FilesApi(api_client)
        outbox_api = OutboxApi(api_client)

        # STEP 1: Upload file to Fax.Plus cloud
        uploaded_path = None
        if file:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(await file.read())
                tmp.flush()
                uploaded = files_api.upload_file(user_id="self", fax_file=tmp.name)
                print(f"UPLOAD RESPONSE: {uploaded.__dict__}")
                uploaded_path = getattr(uploaded, "path", None)
                
        if not uploaded_path:
            print("not uploaded", uploaded_path)
            return {"error": "Upload failed, no cloud path returned"}

        # STEP 2: Build request body
        comment_obj = OutboxComment(text=cover_letter)
        payload = PayloadOutbox(
            from_number=from_number,   # ✅ required
            to=[to_number],
            files=[uploaded_path],
            comment=comment_obj,
            return_ids=True,
        )

        logger.info(f"FAX REQUEST OBJECT: {payload.__dict__}")

        # # STEP 3: Send fax
        response = outbox_api.send_fax(user_id="self", body=payload)
        logger.info(f"FAX RESPONSE: {response.__dict__}")

        print(response.__dict__)
        return {
            "upload_path": uploaded_path,
            "fax_ids": getattr(response, "ids", {}),
            "status": getattr(response, "status", "queued")
        }

    except ApiException as e:
        logger.error(f"Fax.Plus API error: {e.body}")
        return {"error": f"Fax.Plus API error: {e.body}"}
    except Exception as e:
        logger.exception("General error")
        return {"error": str(e)}
