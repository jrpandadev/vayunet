import os
import sys
import argparse
import firebase_admin
from firebase_admin import credentials, firestore, auth

def main():
    parser = argparse.ArgumentParser(description="Provision an authority user in VayuNet.")
    parser.add_argument("--uid", required=True, help="The Firebase UID of the user to promote.")
    args = parser.parse_args()

    # Ensure Firebase Admin SDK credentials are provided via environment
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print("Error: GOOGLE_APPLICATION_CREDENTIALS environment variable must be set.", file=sys.stderr)
        sys.exit(1)

    try:
        # Initialize Firebase Admin app
        if not firebase_admin._apps:
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)

        db = firestore.client()
        user_uid = args.uid

        # Verify the user exists in Firebase Auth
        try:
            user_record = auth.get_user(user_uid)
            print(f"User found: {user_record.email}")
        except Exception as e:
            print(f"Failed to fetch user from Firebase Auth: {e}", file=sys.stderr)
            sys.exit(1)

        # Update the Firestore user profile role
        user_ref = db.collection("users").document(user_uid)
        doc = user_ref.get()

        if not doc.exists:
            print(f"Error: Firestore profile for {user_uid} does not exist. The user must sign in first.", file=sys.stderr)
            sys.exit(1)

        user_ref.update({"role": "authority"})

        print(f"Successfully provisioned authority role for user: {user_uid}")

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
