# Zoom-Past-Meetings-Participants-Retriever


**Zoom Meeting Participants Retriever** is a cross-platform Python script that uses Zoom's API (v2) to retrieve and organize all meeting assistants from a Zoom account onto local storage.



## Installation ##

_Attention: You will need [Python 3.6](https://www.python.org/downloads/) or greater_

```sh
$ git clone https://github.com/Vizardx/Zoom_Meetings_Participants_Retriever
$ cd Zoom_Meetings_Participants_Retriever
$ pip3 install -r requirements.txt
```

## Usage ##

_Attention: You will need a [Zoom Developer account](https://marketplace.zoom.us/) in order to create a [Server-to-Server OAuth app](https://developers.zoom.us/docs/internal-apps) with the required credentials_

1. Create a [server-to-server OAuth app](https://marketplace.zoom.us/user/build), set up your app and collect your credentials (`Account ID`, `Client ID`, `Client Secret`). For questions on this, [reference the docs](https://developers.zoom.us/docs/internal-apps/create/) on creating a server-to-server app. Make sure you activate the app. Follow Zoom's [set up documentation](https://marketplace.zoom.us/docs/guides/build/server-to-server-oauth-app/) or [this video](https://www.youtube.com/watch?v=OkBE7CHVzho) for a more complete walk through.

2. Add the necessary scopes to your app. In your app's _Scopes_ tab, add the following scopes: `account:master`, `account:read:admin`, `account:write:admin`, `information_barriers:read:admin`, `information_barriers:read:master`, `information_barriers:write:admin`, `information_barriers:write:master`, `meeting:master`, `meeting:read:admin`, `meeting:read:admin:sip_dialing`, `meeting:write:admin`, `meeting_token:read:admin:live_streaming`, `meeting_token:read:admin:local_archiving`, `meeting_token:read:admin:local_recording`, `recording:master`, `recording:read:admin`, `recording:write:admin`, `user:master`, `user:read:admin`, `user:write:admin`.

3. Copy **zoom-meeting-particpants.conf.template** to a new file named **zoom-meeting-participants.conf** and fill in your Server-to-Server OAuth app credentials:
```
      {
	      "OAuth": {
		      "account_id": "<ACCOUNT_ID>",
		      "client_id": "<CLIENT_ID>",
		      "client_secret": "<CLIENT_SECRET>"
	      }
      }
```

4. Add environment variables. Open the **Zoom_Meetings_Participants_Retriever.py** file using your editor of choice and fill in the date variables to reflect your environment

Run command:

```sh
python3 Zoom_Meetings_Participants_Retriever.py
```
