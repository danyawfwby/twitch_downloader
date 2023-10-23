import requests
import json
import os
import subprocess


def getM3U8withAccess(videoId, sig, token):
    url = f"https://usher.ttvnw.net/vod/{videoId}.m3u8?allow_source=true&sig={sig}&token={token}"
    r = requests.get(url)
    m3u8 = r.text
    if(m3u8):
        link = m3u8.split("http")[1].split(".m3u8")[0]
        if(link):
            return "http"+link+".m3u8"

def getVideoAccess(videoId, clientId, deviceId):
    variables = {"isLive":False,"login":"","isVod":True,"vodID": f"{videoId}","playerType":"site"}
    headers = {'Client-ID': clientId, 'Device-ID': deviceId}
    payload = {"operationName":"PlaybackAccessToken_Template","query":"query PlaybackAccessToken_Template($login: String!, $isLive: Boolean!, $vodID: ID!, $isVod: Boolean!, $playerType: String!) {  streamPlaybackAccessToken(channelName: $login, params: {platform: \"web\", playerBackend: \"mediaplayer\", playerType: $playerType}) @include(if: $isLive) {    value    signature    __typename  }  videoPlaybackAccessToken(id: $vodID, params: {platform: \"web\", playerBackend: \"mediaplayer\", playerType: $playerType}) @include(if: $isVod) {    value    signature    __typename  }}","variables":variables}
    data = json.dumps(payload)
    r = requests.post("https://gql.twitch.tv/gql", headers=headers, data=data)
    return r.json()

def getInitData(videoId):
    r = requests.get(f"https://www.twitch.tv/videos/{videoId}")
    html = r.text
    clientidPos = html.find("clientId");
    fromclient = html[clientidPos:]
    commonOptionsPos = fromclient.find("commonOptions")
    data = {"device_id":r.cookies['unique_id'],"client_id": fromclient[:commonOptionsPos].split('"')[1]}
    return data

def getM3U8byVideoId(videoId):
    data = getInitData(videoId)
    clientId = data["client_id"]
    deviceId = data["device_id"]
    videoAccess = getVideoAccess(videoId, clientId, deviceId)
    if("data" in videoAccess):
        videoAccess = videoAccess["data"]["videoPlaybackAccessToken"]
        if(videoAccess):
            token = videoAccess.get("value")
            signature = videoAccess.get("signature")
            return getM3U8withAccess(videoId, signature, token)

def parseUrl(url):
    url = url.split("/")
    return list(filter(None, url))[-1]

def downloadVideo(url, to=os.getcwd()):
    try:
        videoId = parseUrl(url)
        m3u8_link = getM3U8byVideoId(videoId)
        file_name = f"{videoId}.mp4"
        ffmpeg = f"{os.path.dirname(__file__)}\\ffmpeg.exe"
        if(to):
            if not os.path.exists(to):
                os.makedirs(to)
        if(m3u8_link):
            command = f"\"{ffmpeg}\" -i \"{m3u8_link}\" -c copy -bsf:a aac_adtstoasc \"{to}\\{file_name}\" -y"
            print(command)
            process = subprocess.Popen(command, stdout=subprocess.PIPE)
            output, error = process.communicate()
            return file_name
    except:
        return False