import threading
import requests
import json
import os, signal
import subprocess
import re
import sys
from time import strftime, sleep, time

ORIGIN = "https://www.twitch.tv/"

def setNickname(nickname):
    if(not nickname):
        nickname = input("Input nickname or video id. Example:" \
                         "\n- https://www.twitch.tv/Nickname\n- https://www.twitch.tv/videos/123456" \
                            "\n- Nickname\n- videos/123456\n")
    return nickname

def setTimer(duration):
    if(isinstance(duration, int)):
        timer= time()+duration
    return timer or None

def getId(url):
    return (list(filter(None, url.split("/"))) or [""])[-1]

def isVideo(url):
    return url.split(ORIGIN)[-1].startswith('videos/')

def getUniqueId(request):
    return request.cookies.get("unique_id")

def getClientId(request):
    return (re.findall('clientId="(\w+)"', request.text) or [""])[0]

def getQuery(request):
    query = (re.findall("query='(.+?)'", request.text) or [""])[0]
    return re.sub('"', '\\"', query)

def getGqlVars(isVideo, id):
    return {
        "isLive": not bool(isVideo),
        "login": id if not isVideo else "",
        "isVod": bool(isVideo),
        "vodID": id if isVideo else "",
        "playerType":"site"
        }

def getBody(request, query):
    body = (re.findall("bodyBase=(.+?);", request.text) or [""])[0]
    body = re.sub("([a-zA-Z0-9-]+):", r'"\1":', body)
    body = body.replace(":query", f':"{query}"')
    return json.loads(body)

def getInitData(url):
    request = requests.get(url)
    id_ = getId(url)
    isVideo_ = isVideo(url)
    uniqueId_ = getUniqueId(request)
    clientId_ = getClientId(request)
    gqlvars_ = getGqlVars(isVideo_, id_)
    query = getQuery(request)
    body_ = getBody(request, query)
    
    return {'Client-ID': clientId_, 'Device-ID': uniqueId_}


def getGqlTempPayload(variables):
    payload = {"operationName":"PlaybackAccessToken_Template","query":"query PlaybackAccessToken_Template($login: String!, $isLive: Boolean!, $vodID: ID!, $isVod: Boolean!, $playerType: String!) {  streamPlaybackAccessToken(channelName: $login, params: {platform: \"web\", playerBackend: \"mediaplayer\", playerType: $playerType}) @include(if: $isLive) {    value    signature    __typename  }  videoPlaybackAccessToken(id: $vodID, params: {platform: \"web\", playerBackend: \"mediaplayer\", playerType: $playerType}) @include(if: $isVod) {    value    signature    __typename  }}","variables":variables}
    return json.dumps(payload)

def getAccessWithVariables(variables, headers):
    payload = getGqlTempPayload(variables)
    respjson = requests.post("https://gql.twitch.tv/gql", headers=headers, data=payload).json() or {}
    return respjson.get("data") or {}

def getAccess(isVideo, id, headers):
    variables = getGqlVars(isVideo, id)
    access = getAccessWithVariables(variables, headers)
    return access.get("videoPlaybackAccessToken") or access.get("streamPlaybackAccessToken")

def getM3U8withAccess(url):
    r = requests.get(url)
    return (re.findall("https.+?m3u8", r.text) or [""])[0]

def getM3U8(isVideo, videoId, sig, token):
    isVideo = "vod" if isVideo else "api/channel/hls"
    url = f"https://usher.ttvnw.net/{isVideo}/{videoId}.m3u8?allow_source=true&sig={sig}&token={token}"
    m3u8 = getM3U8withAccess(url)
    return m3u8

def getM3U8byInput(nickname):
    url = f"{ORIGIN}{nickname}"
    headers = getInitData(url)
    id, isVideo = list(reversed(["", *url.split("twitch.tv/")[-1].split("/")][-2:]))
    if(access:= getAccess(isVideo, id, headers)):
        token = access.get("value") or {}
        signature = access.get("signature") or {}
        return [id, getM3U8(isVideo, id, signature, token)]
    
def ffmpegsubopen(m3u8_link, filename):
    ffmpeg = f"{os.path.dirname(__file__)}\\ffmpeg.exe"
    return subprocess.Popen([ffmpeg, "-i", m3u8_link, "-c", "copy", "-bsf:a", "aac_adtstoasc",f"{filename}.mp4", "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def waitffmpeg(t):
    while getattr(t, "do_run", True):
        sleep(1)

def ffmpegstart(m3u8_link, filename):
    t = threading.currentThread()
    process = ffmpegsubopen(m3u8_link, filename)
    waitffmpeg(t)
    os.kill(process.pid, signal.CTRL_C_EVENT)

def download(nickname = (sys.argv[1:] or [""])[0], filename = "", duration = None):
    try:
        nickname = setNickname(nickname)
        timer = setTimer(duration)
        filename, m3u8_link = getM3U8byInput(nickname)
        if(m3u8_link):
            thread = threading.Thread(target=ffmpegstart, args=(m3u8_link,filename,))
            thread.start()
            while(getM3U8byInput(nickname) and ((not locals().get("timer")) or (time() < timer))):
                sleep(1)
    except Exception as e:
        pass
    finally:
        if(locals().get("thread")):
            thread.do_run = False



if __name__ == "__main__":    
    download()
