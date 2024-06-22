# hubspot.py

import json
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import base64
import hashlib
from integrations.integration_item import IntegrationItem
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

CLIENT_ID = 'your_hubspot_client_id'
CLIENT_SECRET = 'your_hubspot_client_secret'
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
authorization_url = f'https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=contacts%20content'

encoded_client_id_secret = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()

async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode('utf-8')).decode('utf-8')

    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', json.dumps(state_data), expire=600)

    auth_url = f'{authorization_url}&state={encoded_state}'
    return auth_url

async def oauth2callback_hubspot(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error_description'))
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    state_data = json.loads(base64.urlsafe_b64decode(encoded_state).decode('utf-8'))

    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')

    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')

    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://api.hubapi.com/oauth/v1/token',
            data={
                'grant_type': 'authorization_code',
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'redirect_uri': REDIRECT_URI,
                'code': code,
            },
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
            }
        )

    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=600)

    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)

async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    credentials = json.loads(credentials)
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')

    return credentials

# hubspot.py

async def create_integration_item_metadata_object(response_json, item_type, parent_id=None, parent_name=None):
    integration_item_metadata = IntegrationItem(
        id=response_json.get('id', None),
        name=response_json.get('name', None),
        type=item_type,
        parent_id=parent_id,
        parent_path_or_name=parent_name,
    )
    return integration_item_metadata

async def get_items_hubspot(credentials):
    async with httpx.AsyncClient() as client:
        headers = {
            'Authorization': f'Bearer {credentials["access_token"]}',
            'Content-Type': 'application/json',
        }
        response = await client.get('https://api.hubapi.com/contacts/v1/lists/all/contacts/all', headers=headers)
    
    contacts = response.json().get('contacts', [])
    list_of_integration_item_metadata = []
    
    for contact in contacts:
        item = await create_integration_item_metadata_object(contact, 'Contact')
        list_of_integration_item_metadata.append(item)
    
    print(f'list_of_integration_item_metadata: {list_of_integration_item_metadata}')
    return list_of_integration_item_metadata