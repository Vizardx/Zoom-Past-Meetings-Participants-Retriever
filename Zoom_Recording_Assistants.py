import base64
import datetime
import json
import re
import sys as system
import pandas as pd
import time
import requests
from urllib.parse import quote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Crea una sesión de requests
session = requests.Session()

# Crea un objeto Retry
retry = Retry(
    total=5,
    backoff_factor=0.1,
    status_forcelist=[500, 502, 503, 504],
)

# Monta el adaptador HTTP para todas las URLs
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

CONF_PATH = "zoom-recording-downloader.conf"
with open(CONF_PATH, encoding="utf-8-sig") as json_file:
    CONF = json.loads(json_file.read())

ACCOUNT_ID = CONF["OAuth"]["account_id"]
CLIENT_ID = CONF["OAuth"]["client_id"]
CLIENT_SECRET = CONF["OAuth"]["client_secret"]

APP_VERSION = "3.0 (OAuth)"

API_ENDPOINT_USER_LIST = "https://api.zoom.us/v2/users"

# Set these variables to the earliest recording date you wish to download
RECORDING_START_YEAR = 2023
RECORDING_START_MONTH = 9
RECORDING_START_DAY = 1
RECORDING_END_DATE = datetime.date.today()

class Color:
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    DARK_CYAN = "\033[36m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def load_access_token():
    """ OAuth function, thanks to https://github.com/freelimiter
    """
    url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={ACCOUNT_ID}"

    client_cred = f"{CLIENT_ID}:{CLIENT_SECRET}"
    client_cred_base64_string = base64.b64encode(client_cred.encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": f"Basic {client_cred_base64_string}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = json.loads(requests.request("POST", url, headers=headers).text)

    global ACCESS_TOKEN
    global AUTHORIZATION_HEADER

    try:
        ACCESS_TOKEN = response["access_token"]
        AUTHORIZATION_HEADER = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

    except KeyError:
        print(f"{Color.RED}### The key 'access_token' wasn't found.{Color.END}")


def get_users():
    """ loop through pages and return all users
    """
    response = requests.get(url=API_ENDPOINT_USER_LIST, headers=AUTHORIZATION_HEADER)

    if not response.ok:
        print(response)
        print(
            f"{Color.RED}### Could not retrieve users. Please make sure that your access "
            f"token is still valid{Color.END}"
        )

        system.exit(1)

    page_data = response.json()
    total_pages = int(page_data["page_count"]) + 1

    all_users = []

    for page in range(1, total_pages):
        url = f"{API_ENDPOINT_USER_LIST}?page_number={str(page)}"
        user_data = requests.get(url=url, headers=AUTHORIZATION_HEADER).json()
        users = ([
            (
                user["email"],
                user["id"],
                user["first_name"],
                user["last_name"]
            )
            for user in user_data["users"]
        ])

        all_users.extend(users)
        page += 1

    return all_users


def get_recordings(email, page_size, rec_start_date, rec_end_date):
    return {
        "userId": email,
        "page_size": page_size,
        "from": rec_start_date,
        "to": rec_end_date
    }


def per_delta(start, end, delta):
    """ Generator used to create deltas for recording start and end dates
    """
    curr = start
    while curr < end:
        yield curr, min(curr + delta, end)
        curr += delta


def list_recordings(email):
    """ Start date now split into YEAR, MONTH, and DAY variables (Within 6 month range)
        then get recordings within that range
    """
    recordings = []

    for start, end in per_delta(
        datetime.date(RECORDING_START_YEAR, RECORDING_START_MONTH, RECORDING_START_DAY),
        RECORDING_END_DATE,
        datetime.timedelta(days=30)
    ):
        post_data = get_recordings(email, 300, start, end)
        response = requests.get(
            url=f"https://api.zoom.us/v2/users/{email}/recordings",
            headers=AUTHORIZATION_HEADER,
            params=post_data
        )
        recordings_data = response.json()
        recordings.extend(recordings_data["meetings"])

    return recordings


def get_meeting_participants(meeting_id, user_info, topic, duration, uuid, ):
    # Doble codificación del UUID de la reunión si comienza con '/' o contiene '//'
    if meeting_id.startswith('/') or '//' in meeting_id:
        meeting_id = quote(quote(meeting_id, safe=''), safe='')

    all_participants = []
    next_page_token = ''

    while True:
        url = f"https://api.zoom.us/v2/report/meetings/{meeting_id}/participants"
        params = {
            'page_size': 300,
            'next_page_token': next_page_token
        }
        response = session.get(url=url, headers=AUTHORIZATION_HEADER, params=params)

        # Verifica que la respuesta no esté vacía.
        if not response.content:
            raise ValueError(f"La respuesta de la API está vacía.")

        # Verifica que la respuesta esté en formato JSON.
        if response.headers["Content-Type"] != "application/json;charset=UTF-8":
            print(response.content)
            raise ValueError(f"La respuesta de la API no está en formato JSON.")

        # Obtiene la respuesta de la API como un objeto Python.
        data = response.json()

        # Verifica si 'participants' está en data.
        if 'participants' in data:
            # Añade la información del usuario, el tema y la duración a cada participante.
            for participant in data["participants"]:
                participant["user_info"] = user_info
                participant["topic"] = topic
                participant["duration"] = duration
                participant["uuid"] = uuid

            all_participants.extend(data["participants"])

        else:
            print(f"No se encontraron participantes para la reunión {meeting_id}")

        # Pausa durante 0.5 segundos para evitar alcanzar el límite de la tasa de solicitudes.
        time.sleep(0.5)

        # Si no hay un token para la siguiente página, entonces hemos llegado al final.
        if not data.get('next_page_token'):
            break

        next_page_token = data['next_page_token']
        print("Next_Page_Token reinicado!")

    return all_participants

# Funciones de preprocesamiento de datos para sacar columnas cruzables
def extract_email(name):
    match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', name)
    return match.group() if match else None

def extract_dni(name):
    match = re.search(r'\b\d{8}[A-Z]\b', name)
    return match.group() if match else None

def extract_full_name(name):
    match = re.search(r'^(.*?)(?=\b\d{8}[A-Z]\b|\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b|$)', name)
    result = match.group().strip() if match else None
    return result if result and ' ' in result else None

def main():
    # Carga el token de acceso
    load_access_token()
    last_token_load_time = time.time()
    
    
    # Obtiene todos los usuarios
    print("Obteniendo todos los usuarios...")
    users = get_users()

    all_participants = []

    for email, user_id, first_name, last_name in users:
        userInfo = (
            f"{first_name} {last_name} - {email}" if first_name and last_name else f"{email}"
        )
        print(f"\nProcesando el usuario {userInfo}")
        
        # Obtiene todas las grabaciones para el usuario en el plazo especificado
        recordings = list_recordings(user_id)

        for recording in recordings:
            meeting_id = recording["uuid"]
            print(f"Obteniendo participantes para la reunión {meeting_id}")
            
            participants = get_meeting_participants(meeting_id, userInfo, recording['topic'], recording['duration'], recording['uuid'])
            all_participants.extend(participants)

            # Recarga el token de acceso cada 55 minutos
            if time.time() - last_token_load_time >= 55 * 60:
                load_access_token()
                last_token_load_time = time.time()
                print("Reiniciando Token . . .")

    df = pd.DataFrame(all_participants)

    df['Email'] = df['name'].apply(extract_email)
    df['DNI'] = df['name'].apply(extract_dni)
    df['Nombre completo'] = df['name'].apply(extract_full_name)
    df['No procesable'] = df.apply(lambda row: None if row['Email'] or row['DNI'] or row['Nombre completo'] else row['name'], axis=1)
    df.to_csv("Zoom_Assistants_01-09-23__16-01-23.csv", index=False, encoding='utf-8')
    print("Proceso finalizado con exito!")

if __name__ == "__main__":
    main()