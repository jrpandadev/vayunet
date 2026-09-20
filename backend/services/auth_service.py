import os
from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import auth, credentials, firestore

security = HTTPBearer()

def get_firebase_app():
    if not firebase_admin._apps:
        if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            # For local dev without credentials, we might fail or mock, but the requirement is strict validation.
            pass
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
    return firebase_admin.get_app()

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verifies the Firebase ID token and returns the decoded token payload.
    This guarantees the user is actually authenticated by Firebase.
    """
    token = credentials.credentials
    get_firebase_app()
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid authentication credentials: {e}")

def require_authority(user: dict = Depends(get_current_user)):
    """
    Looks up the authoritative role from Firestore using the trusted Firebase UID.
    """
    get_firebase_app()
    db = firestore.client()
    user_uid = user.get("uid")
    if not user_uid:
        raise HTTPException(status_code=401, detail="No UID found in token")

    doc_ref = db.collection("users").document(user_uid)
    doc = doc_ref.get()

    if not doc.exists:
        raise HTTPException(status_code=403, detail="User profile not found")

    role = doc.to_dict().get("role")
    if role != "authority":
        raise HTTPException(status_code=403, detail="Authority privileges required")

    return user
