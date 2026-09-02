import os
import sys
import pickle
import time
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from config import BASE_DIR

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# YouTube Upload OAuth Scopes (Upload + Commenting)
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

def get_authenticated_service():
    """Authenticates the user using client_secret.json and returns the YouTube API client."""
    client_secret_file = BASE_DIR / "client_secret.json"
    token_file = BASE_DIR / "token.pickle"
    
    if not client_secret_file.exists():
        print("\n" + "="*60)
        print("[WARNING] YOUTUBE UPLOAD CONFIGURATION MISSING")
        print("="*60)
        print("To enable automatic uploads to YouTube, please follow these steps:")
        print("1. Go to Google Cloud Console (https://console.cloud.google.com/)")
        print("2. Enable the 'YouTube Data API v3'.")
        print("3. Create an OAuth 2.0 Client ID (Desktop Application).")
        print("4. Download the JSON credentials file, rename it to 'client_secret.json'")
        print(f"   and place it in your project folder at: {client_secret_file}")
        print("="*60 + "\n")
        return None
        
    credentials = None
    if token_file.exists():
        with open(token_file, 'rb') as token:
            credentials = pickle.load(token)
            
    if not credentials or not credentials.valid:
        refreshed = False
        if credentials and credentials.expired and credentials.refresh_token:
            print("Refreshing expired OAuth credentials...")
            try:
                credentials.refresh(Request())
                refreshed = True
            except Exception as e:
                print(f"[!] Warning: Token refresh failed ({e}). Re-authenticating...")
                credentials = None
                
        if not refreshed or not credentials or not credentials.valid:
            # If running in headless environment (GitHub Actions), fail with clear message
            if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
                raise RuntimeError(
                    "\n" + "="*60 +
                    "\n[CRITICAL] YOUTUBE_TOKEN_BASE64 IN GITHUB SECRETS HAS EXPIRED!" +
                    "\nIn Google Cloud Console, if the app is in 'Testing' mode, tokens expire every 7 days." +
                    "\nTo fix: Change OAuth status to 'In Production' in Google Cloud, re-authenticate locally," +
                    "\nrun 'python encode_tokens.py' and update YOUTUBE_TOKEN_BASE64 in GitHub Secrets." +
                    "\n" + "="*60
                )
            print("Opening browser for YouTube OAuth authorization...")
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_file), SCOPES)
            credentials = flow.run_local_server(port=0)
            
        with open(token_file, 'wb') as token:
            pickle.dump(credentials, token)
            print("Authentication token saved locally for future automatic uploads.")
            
    return build('youtube', 'v3', credentials=credentials)

def upload_short(video_path, title, description, tags=None, category_id="27", privacy_status="public", hide_likes=True, comment_text=None):
    """Uploads a video to YouTube as a Short.
    
    Args:
        video_path (Path or str): Path to the video file
        title (str): Video title
        description (str): Video description with hashtags
        tags (list): List of search keywords/tags
        category_id (str): YouTube Category ID ('27'=Education, '24'=Entertainment, '22'=People & Blogs)
        privacy_status (str): 'public', 'private', or 'unlisted'
        comment_text (str): Optional text for the first automated comment
    """
    youtube = get_authenticated_service()
    if not youtube:
        print("Upload skipped: YouTube API is not configured yet.")
        return None
        
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"Upload error: Video file not found at {video_path}")
        return None
        
    if tags is None:
        tags = ["shorts", "viral", "fyp"]
        
    # Ensure title fits within YouTube's 100 character limit
    if len(title) > 100:
        title = title[:97] + "..."
        
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': category_id
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': False,
            'showLikes': not hide_likes
        }
    }
    
    print(f"\n[YOUTUBE UPLOAD] Uploading '{title}' to YouTube ({privacy_status.upper()})...")
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype='video/mp4')
    
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploading... {int(status.progress() * 100)}% completed.")
            
    video_id = response.get('id')
    video_url = f"https://youtube.com/shorts/{video_id}"
    
    # Upload custom thumbnail if generated in video folder
    thumb_path = video_path.parent / "thumbnail.jpg"
    if thumb_path.exists():
        try:
            print("[YOUTUBE UPLOAD] Uploading high-CTR vertical thumbnail to YouTube...")
            thumb_media = MediaFileUpload(str(thumb_path), mimetype='image/jpeg')
            youtube.thumbnails().set(videoId=video_id, media_body=thumb_media).execute()
            print("Custom thumbnail uploaded successfully!")
        except Exception as te:
            print(f"Thumbnail upload note: {te}")
            
    # Post first automated comment
    if video_id and comment_text:
        try:
            print(f"[YOUTUBE UPLOAD] Posting first automated comment: '{comment_text}'...")
            youtube.commentThreads().insert(
                part="snippet",
                body={
                    "snippet": {
                        "videoId": video_id,
                        "topLevelComment": {
                            "snippet": {
                                "textOriginal": comment_text
                            }
                        }
                    }
                }
            ).execute()
            print("First comment posted successfully!")
        except Exception as ce:
            print(f"Comment post notice (note: requires re-authenticating scopes): {ce}")

    print("\n" + "="*60)
    print("[SUCCESS] YouTube Short uploaded successfully!")
    print(f"   Video URL: {video_url}")
    print("="*60 + "\n")
    return video_url

if __name__ == "__main__":
    print("Testing YouTube service authentication...")
    service = get_authenticated_service()
    if service:
        print("YouTube API service initialized successfully.")
