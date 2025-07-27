# C:/Development/Projects/Demented-Discord-Bot/data/web_server.py

import time
import logging
import os
from functools import wraps
from flask import Flask, request, Response
from threading import Thread
from waitress import serve
import requests
from data.database_manager import store_oauth_tokens, delete_oauth_tokens

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

# Set up logging
logger = logging.getLogger('webserver')

# Create Flask app
app = Flask(__name__)
start_time = time.time()

# Global variable to hold the bot instance, allowing communication
bot_instance = None

DISCORD_API_URL = "https://discord.com/api/v10"

# Load the public key for verification
CLIENT_PUBLIC_KEY = os.getenv('CLIENT_PUBLIC_KEY')
if not CLIENT_PUBLIC_KEY:
    logger.warning("CLIENT_PUBLIC_KEY not found in .env file. Webhook verification will fail.")
    verify_key = None
else:
    verify_key = VerifyKey(bytes.fromhex(CLIENT_PUBLIC_KEY))


# --- NEW: Decorator for Signature Verification ---
def verify_discord_signature(f):
    """A decorator to verify the signature of incoming Discord webhooks."""
    @wraps(f)
    def decorator(*args, **kwargs):
        if not verify_key:
            logger.error("Cannot verify webhook: CLIENT_PUBLIC_KEY is not configured.")
            return 'server configuration error', 500

        signature = request.headers.get('X-Signature-Ed25519')
        timestamp = request.headers.get('X-Signature-Timestamp')
        body = request.data.decode('utf-8')

        if not signature or not timestamp:
            logger.warning("Webhook received from an unverified source (missing signature headers).")
            return 'invalid request', 401

        try:
            message = timestamp.encode() + body.encode()
            verify_key.verify(message, bytes.fromhex(signature))
        except BadSignatureError:
            logger.error("Invalid signature on incoming webhook!")
            return 'invalid request signature', 401
        except Exception as e:
            logger.error(f"Error during signature verification: {e}")
            return 'internal server error', 500

        return f(*args, **kwargs)
    return decorator


# --- HTML Templates ---
HTML_HEADER = '''
<!DOCTYPE html>
<html>
<head>
    <title>Demented Bot</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #2c2f33; color: #ffffff; text-align: center; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .container { max-width: 800px; margin: 0 auto; background-color: #23272a; padding: 20px 40px; border-radius: 10px; box-shadow: 0 0 15px rgba(0,0,0,0.5); }
        h1 { color: #7289da; }
        p { font-size: 18px; line-height: 1.6; }
        .status { font-size: 24px; font-weight: bold; margin: 20px 0; }
        .status.online { color: #43b581; }
        .status.error { color: #f04747; }
        .info { text-align: left; margin: 20px auto; width: fit-content; }
        .info p { margin: 5px 0; }
        strong { color: #7289da; }
    </style>
</head>
<body>
    <div class="container">
'''

HTML_FOOTER = '''
    </div>
</body>
</html>
'''


# --- Routes ---
@app.route('/')
def home():
    """Render status page with uptime information."""
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    uptime_seconds = int(time.time() - start_time)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 0:
        uptime = f"{days}d {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        uptime = f"{hours}h {minutes}m {seconds}s"
    else:
        uptime = f"{minutes}m {seconds}s"
    content = f'''<h1>Demented Bot</h1><div class="status online">✅ Online</div><div class="info"><p><strong>Uptime:</strong> {uptime}</p><p><strong>Version:</strong> 2.0</p><p><strong>Last checked:</strong> {current_time}</p></div>'''
    return HTML_HEADER + content + HTML_FOOTER


@app.route('/health')
def health():
    """Simple health check endpoint for monitoring services."""
    bot_status = "connected" if bot_instance and bot_instance.is_ready() else "disconnected"
    return {"status": "healthy", "uptime": int(time.time() - start_time), "bot_status": bot_status}


@app.route('/auth/callback')
def auth_callback():
    """Handles the OAuth2 redirect from Discord."""
    code = request.args.get('code')
    state = request.args.get('state')
    if not code or not state:
        logger.warning("Callback received with missing code or state.")
        content = '''<h1>Verification Error</h1><div class="status error">❌ Failed</div><p>Verification data was missing from your request. This is often caused by a <strong>VPN, ad-blocker, or privacy extension</strong>.</p><p>Please try again in an Incognito/Private window, or temporarily disable these extensions.</p>'''
        return HTML_HEADER + content + HTML_FOOTER, 400
    try:
        guild_id = int(state)
    except (ValueError, TypeError):
        logger.error(f"Callback received with invalid state parameter: {state}")
        content = '<h1>Error</h1><p>Invalid state parameter received.</p>'
        return HTML_HEADER + content + HTML_FOOTER, 400
    token_data = {'client_id': os.getenv('CLIENT_ID'), 'client_secret': os.getenv('CLIENT_SECRET'),
                  'grant_type': 'authorization_code', 'code': code, 'redirect_uri': os.getenv('REDIRECT_URI')}
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    try:
        token_res = requests.post(f"{DISCORD_API_URL}/oauth2/token", data=token_data, headers=headers)
        token_res.raise_for_status()
        token_json = token_res.json()
        user_headers = {'Authorization': f'Bearer {token_json["access_token"]}'}
        user_info_res = requests.get(f"{DISCORD_API_URL}/users/@me", headers=user_headers)
        user_info_res.raise_for_status()
        user_json = user_info_res.json()
        user_id = int(user_json['id'])
        username = user_json['username']
        store_oauth_tokens(user_id, token_json['access_token'], token_json['refresh_token'], token_json['expires_in'])
        logger.info(f"Successfully authorized and stored tokens for {username} ({user_id}).")
        content = f'''<h1>Verification Successful!</h1><div class="status online">✅ Success</div><p>Thank you, <strong>{username}</strong>. You are now verified!</p><p>You can close this window and return to Discord.</p>'''
        return HTML_HEADER + content + HTML_FOOTER
    except requests.exceptions.RequestException as e:
        logger.error(f"OAuth token exchange failed: {e.response.text if e.response else e}", exc_info=True)
        content = '<h1>Error</h1><p>An error occurred while communicating with Discord. Please try again later.</p>'
        return HTML_HEADER + content + HTML_FOOTER, 500


@app.route('/discord/webhook', methods=['POST'])
@verify_discord_signature  # Apply the decorator here
def discord_webhook_handler():
    """
    Handles incoming webhooks from Discord, including PINGs and deauthorizations.
    Signature is verified by the @verify_discord_signature decorator.
    """
    data = request.get_json()

    # Handle PING (Verification)
    if data.get('type') == 0:
        logger.info("Received PING from Discord. Responding with 204.")
        return Response(status=204)

    # Handle actual events
    if not bot_instance or not bot_instance.is_ready():
        logger.error("Webhook event received, but bot instance is not ready. Aborting.")
        return {"status": "error", "message": "Bot is not ready"}, 503

    event_payload = data.get('event', {})
    event_type = event_payload.get('type')
    event_data = event_payload.get('data', {})

    if event_type == 'APPLICATION_DEAUTHORIZED':
        user_id_str = event_data.get('user', {}).get('id')
        if not user_id_str:
            logger.warning(f"Received DEAUTHORIZED event with no user ID: {data}")
        else:
            logger.info(f"Received deauthorization webhook for user ID: {user_id_str}")
            user_id = int(user_id_str)
            delete_oauth_tokens(user_id)
            verification_cog = bot_instance.get_cog("Verification")
            if verification_cog:
                verification_cog.schedule_role_revert(user_id)
            else:
                logger.error("Could not find VerificationCog to schedule role revert.")

    elif event_type == 'APPLICATION_AUTHORIZED':
        user_id_str = event_data.get('user', {}).get('id')
        logger.info(f"Received authorization event for user ID: {user_id_str}. No action taken.")

    else:
        logger.info(f"Received unhandled webhook event type: {event_type}")

    # Acknowledge the event
    logger.debug(f"Successfully processed event '{event_type}'. Acknowledging with 204.")
    return Response(status=204)


def run():
    """Run the web server using waitress for production."""
    port = int(os.getenv('PORT', 8080))
    logger.info(f"Starting web server on port {port}")
    serve(app, host='0.0.0.0', port=port, threads=4)


def keep_alive(bot):
    """Start the web server in a background thread and give it the bot instance."""
    global bot_instance
    bot_instance = bot
    t = Thread(target=run, daemon=True)
    t.start()
    logger.info("Web server thread started")
    return t