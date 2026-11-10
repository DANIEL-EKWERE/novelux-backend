"""Talking to each network.

Every platform has:
  verify(account)          → (ok, "who/what we're connected to" | error)
  publish(account, ctx)    → (external_id, url)  or raises PublishError

`ctx` is a PostContext: the text for this network, the link, the title, and
the media (public URLs plus a way to read the bytes for networks that need an
upload instead of a URL).
"""
import time

import requests

GRAPH = 'https://graph.facebook.com/v21.0'
THREADS = 'https://graph.threads.net/v1.0'
TIMEOUT = 60


class PublishError(Exception):
    pass


class PostContext:
    def __init__(self, text, link='', title='', images=None, video=None):
        self.text = text or ''
        self.link = link or ''
        self.title = title or ''
        self.images = images or []   # [Media]
        self.video = video           # Media or None

    def text_with_link(self, sep='\n\n'):
        if self.link and self.link not in self.text:
            return (self.text + sep + self.link).strip()
        return self.text


class Media:
    """A file attached to a post: a public URL and its bytes on demand."""
    def __init__(self, url, open_bytes, name='file', content_type='application/octet-stream'):
        self.url = url
        self._open = open_bytes
        self.name = name
        self.content_type = content_type
        self._data = None

    @property
    def data(self):
        if self._data is None:
            self._data = self._open()
        return self._data


def _json(resp):
    try:
        return resp.json()
    except ValueError:
        return {'raw': resp.text[:500]}


def _err(resp, where):
    body = _json(resp)
    msg = (body.get('error', {}) or {}).get('message') if isinstance(body.get('error'), dict) else None
    msg = msg or body.get('detail') or body.get('description') or body.get('message') or body.get('raw') or str(body)[:300]
    return PublishError(f'{where}: {resp.status_code} — {msg}')


def _check(resp, where):
    if resp.status_code >= 400:
        raise _err(resp, where)
    data = _json(resp)
    if isinstance(data, dict) and data.get('error') and not data.get('id'):
        raise _err(resp, where)
    return data


# ── Facebook Page ─────────────────────────────────────────────────────────────

class Facebook:
    fields = [('page_id', 'Page ID', False), ('page_token', 'Page access token', True)]

    @staticmethod
    def verify(acc):
        r = requests.get(f"{GRAPH}/{acc.config.get('page_id')}",
                         params={'fields': 'name,link', 'access_token': acc.secrets.get('page_token')}, timeout=TIMEOUT)
        d = _check(r, 'Facebook')
        return f"Page: {d.get('name')}"

    @staticmethod
    def publish(acc, ctx):
        page, token = acc.config.get('page_id'), acc.secrets.get('page_token')
        if ctx.video:
            d = _check(requests.post(f'{GRAPH}/{page}/videos', data={
                'file_url': ctx.video.url, 'description': ctx.text_with_link(), 'title': ctx.title,
                'access_token': token}, timeout=TIMEOUT), 'Facebook video')
            return d['id'], f"https://www.facebook.com/{page}/videos/{d['id']}"
        if len(ctx.images) == 1:
            d = _check(requests.post(f'{GRAPH}/{page}/photos', data={
                'url': ctx.images[0].url, 'caption': ctx.text_with_link(), 'access_token': token},
                timeout=TIMEOUT), 'Facebook photo')
            pid = d.get('post_id') or d['id']
            return pid, f'https://www.facebook.com/{pid}'
        data = {'message': ctx.text, 'access_token': token}
        if ctx.link:
            data['link'] = ctx.link
        for i, img in enumerate(ctx.images):
            up = _check(requests.post(f'{GRAPH}/{page}/photos', data={
                'url': img.url, 'published': 'false', 'access_token': token}, timeout=TIMEOUT), 'Facebook photo')
            data[f'attached_media[{i}]'] = '{"media_fbid":"%s"}' % up['id']
        d = _check(requests.post(f'{GRAPH}/{page}/feed', data=data, timeout=TIMEOUT), 'Facebook post')
        return d['id'], f"https://www.facebook.com/{d['id']}"


# ── Instagram (Business/Creator account linked to the Facebook Page) ─────────

def _wait_container(base, cid, token, field='status_code', minutes=6):
    """Videos are processed before they can be published."""
    deadline = time.time() + minutes * 60
    while time.time() < deadline:
        d = _json(requests.get(f'{base}/{cid}', params={'fields': field, 'access_token': token}, timeout=TIMEOUT))
        state = d.get(field)
        if state in ('FINISHED', 'PUBLISHED'):
            return
        if state in ('ERROR', 'EXPIRED'):
            raise PublishError(f'Video processing failed ({state}).')
        time.sleep(5)
    raise PublishError('Video took too long to process — try again later.')


class Instagram:
    fields = [('ig_user_id', 'Instagram account ID', False), ('access_token', 'Access token', True)]

    @staticmethod
    def verify(acc):
        r = requests.get(f"{GRAPH}/{acc.config.get('ig_user_id')}",
                         params={'fields': 'username', 'access_token': acc.secrets.get('access_token')}, timeout=TIMEOUT)
        return f"@{_check(r, 'Instagram').get('username')}"

    @staticmethod
    def publish(acc, ctx):
        ig, token = acc.config.get('ig_user_id'), acc.secrets.get('access_token')
        caption = ctx.text_with_link()   # links aren't clickable on Instagram, but readable
        if ctx.video:
            c = _check(requests.post(f'{GRAPH}/{ig}/media', data={
                'media_type': 'REELS', 'video_url': ctx.video.url, 'caption': caption, 'access_token': token},
                timeout=TIMEOUT), 'Instagram reel')
            _wait_container(GRAPH, c['id'], token)
            creation = c['id']
        elif len(ctx.images) == 1:
            creation = _check(requests.post(f'{GRAPH}/{ig}/media', data={
                'image_url': ctx.images[0].url, 'caption': caption, 'access_token': token},
                timeout=TIMEOUT), 'Instagram photo')['id']
        elif ctx.images:
            children = [_check(requests.post(f'{GRAPH}/{ig}/media', data={
                'image_url': img.url, 'is_carousel_item': 'true', 'access_token': token},
                timeout=TIMEOUT), 'Instagram carousel item')['id'] for img in ctx.images[:10]]
            creation = _check(requests.post(f'{GRAPH}/{ig}/media', data={
                'media_type': 'CAROUSEL', 'children': ','.join(children), 'caption': caption,
                'access_token': token}, timeout=TIMEOUT), 'Instagram carousel')['id']
        else:
            raise PublishError('Instagram needs an image or a video.')
        d = _check(requests.post(f'{GRAPH}/{ig}/media_publish', data={
            'creation_id': creation, 'access_token': token}, timeout=TIMEOUT), 'Instagram publish')
        link = _json(requests.get(f"{GRAPH}/{d['id']}", params={'fields': 'permalink', 'access_token': token},
                                  timeout=TIMEOUT)).get('permalink', '')
        return d['id'], link


# ── Threads ───────────────────────────────────────────────────────────────────

class Threads:
    fields = [('user_id', 'Threads user ID', False), ('access_token', 'Access token', True)]

    @staticmethod
    def refresh(acc):
        """Long-lived Threads tokens last 60 days; refreshing extends them."""
        r = requests.get('https://graph.threads.net/refresh_access_token', params={
            'grant_type': 'th_refresh_token', 'access_token': acc.secrets.get('access_token')}, timeout=TIMEOUT)
        if r.status_code < 400 and _json(r).get('access_token'):
            acc.update_secrets(access_token=_json(r)['access_token'])
            acc.save(update_fields=['_secrets'])

    @staticmethod
    def verify(acc):
        r = requests.get(f"{THREADS}/{acc.config.get('user_id')}",
                         params={'fields': 'username', 'access_token': acc.secrets.get('access_token')}, timeout=TIMEOUT)
        return f"@{_check(r, 'Threads').get('username')}"

    @staticmethod
    def publish(acc, ctx):
        Threads.refresh(acc)
        uid, token = acc.config.get('user_id'), acc.secrets.get('access_token')
        text = ctx.text_with_link()
        if ctx.video:
            body = {'media_type': 'VIDEO', 'video_url': ctx.video.url, 'text': text}
        elif len(ctx.images) == 1:
            body = {'media_type': 'IMAGE', 'image_url': ctx.images[0].url, 'text': text}
        elif ctx.images:
            kids = [_check(requests.post(f'{THREADS}/{uid}/threads', data={
                'media_type': 'IMAGE', 'image_url': i.url, 'is_carousel_item': 'true', 'access_token': token},
                timeout=TIMEOUT), 'Threads carousel item')['id'] for i in ctx.images[:20]]
            body = {'media_type': 'CAROUSEL', 'children': ','.join(kids), 'text': text}
        else:
            body = {'media_type': 'TEXT', 'text': text}
        c = _check(requests.post(f'{THREADS}/{uid}/threads', data={**body, 'access_token': token},
                                 timeout=TIMEOUT), 'Threads')
        if ctx.video:
            _wait_container(THREADS, c['id'], token, field='status')
        d = _check(requests.post(f'{THREADS}/{uid}/threads_publish', data={
            'creation_id': c['id'], 'access_token': token}, timeout=TIMEOUT), 'Threads publish')
        link = _json(requests.get(f"{THREADS}/{d['id']}", params={'fields': 'permalink', 'access_token': token},
                                  timeout=TIMEOUT)).get('permalink', '')
        return d['id'], link


# ── X (Twitter) ───────────────────────────────────────────────────────────────

class X:
    fields = [('api_key', 'API key', True), ('api_secret', 'API key secret', True),
              ('access_token', 'Access token', True), ('access_secret', 'Access token secret', True)]
    UPLOAD = 'https://upload.twitter.com/1.1/media/upload.json'

    @staticmethod
    def _session(acc):
        from requests_oauthlib import OAuth1Session
        s = acc.secrets
        return OAuth1Session(s.get('api_key'), client_secret=s.get('api_secret'),
                             resource_owner_key=s.get('access_token'), resource_owner_secret=s.get('access_secret'))

    @staticmethod
    def verify(acc):
        d = _check(X._session(acc).get('https://api.x.com/2/users/me', timeout=TIMEOUT), 'X')
        return f"@{d.get('data', {}).get('username')}"

    @staticmethod
    def _upload_video(sess, media):
        size = len(media.data)
        init = _check(sess.post(X.UPLOAD, data={'command': 'INIT', 'total_bytes': size,
                                                'media_type': media.content_type or 'video/mp4',
                                                'media_category': 'tweet_video'}, timeout=TIMEOUT), 'X video init')
        mid = init['media_id_string']
        chunk = 4 * 1024 * 1024
        for i, start in enumerate(range(0, size, chunk)):
            r = sess.post(X.UPLOAD, data={'command': 'APPEND', 'media_id': mid, 'segment_index': i},
                          files={'media': media.data[start:start + chunk]}, timeout=TIMEOUT * 3)
            if r.status_code >= 400:
                raise _err(r, 'X video upload')
        fin = _check(sess.post(X.UPLOAD, data={'command': 'FINALIZE', 'media_id': mid}, timeout=TIMEOUT), 'X video')
        info = fin.get('processing_info')
        deadline = time.time() + 300
        while info and info.get('state') in ('pending', 'in_progress') and time.time() < deadline:
            time.sleep(info.get('check_after_secs', 5))
            info = _json(sess.get(X.UPLOAD, params={'command': 'STATUS', 'media_id': mid},
                                  timeout=TIMEOUT)).get('processing_info')
        if info and info.get('state') == 'failed':
            raise PublishError(f"X couldn't process the video: {info.get('error', {}).get('message', '')}")
        return mid

    @staticmethod
    def publish(acc, ctx):
        sess = X._session(acc)
        media_ids = []
        if ctx.video:
            media_ids.append(X._upload_video(sess, ctx.video))
        else:
            for img in ctx.images[:4]:
                up = _check(sess.post(X.UPLOAD, files={'media': img.data}, timeout=TIMEOUT), 'X image upload')
                media_ids.append(up['media_id_string'])
        body = {'text': ctx.text_with_link(' ')}
        if media_ids:
            body['media'] = {'media_ids': media_ids}
        d = _check(sess.post('https://api.x.com/2/tweets', json=body, timeout=TIMEOUT), 'X')
        tid = d.get('data', {}).get('id', '')
        return tid, f'https://x.com/i/web/status/{tid}'


# ── TikTok ────────────────────────────────────────────────────────────────────

class TikTok:
    fields = [('client_key', 'Client key', True), ('client_secret', 'Client secret', True),
              ('access_token', 'Access token', True), ('refresh_token', 'Refresh token', True),
              ('privacy_level', 'Privacy (SELF_ONLY until TikTok audits your app)', False)]
    API = 'https://open.tiktokapis.com/v2'

    @staticmethod
    def refresh(acc):
        s = acc.secrets
        if not s.get('refresh_token'):
            return
        r = requests.post(f'{TikTok.API}/oauth/token/', data={
            'client_key': s.get('client_key'), 'client_secret': s.get('client_secret'),
            'grant_type': 'refresh_token', 'refresh_token': s.get('refresh_token')}, timeout=TIMEOUT)
        d = _json(r)
        if r.status_code < 400 and d.get('access_token'):
            acc.update_secrets(access_token=d['access_token'], refresh_token=d.get('refresh_token'))
            acc.save(update_fields=['_secrets'])

    @staticmethod
    def _h(acc):
        return {'Authorization': f"Bearer {acc.secrets.get('access_token')}",
                'Content-Type': 'application/json; charset=UTF-8'}

    @staticmethod
    def verify(acc):
        TikTok.refresh(acc)
        r = requests.post(f'{TikTok.API}/post/publish/creator_info/query/', headers=TikTok._h(acc), timeout=TIMEOUT)
        d = _check(r, 'TikTok')
        if (d.get('error') or {}).get('code') not in (None, 'ok'):
            raise PublishError(f"TikTok: {d['error'].get('message')}")
        return f"@{d.get('data', {}).get('creator_username', '')}"

    @staticmethod
    def publish(acc, ctx):
        TikTok.refresh(acc)
        privacy = acc.config.get('privacy_level') or 'SELF_ONLY'
        caption = ctx.text_with_link(' ')[:2200]
        if ctx.video:
            size = len(ctx.video.data)
            init = _check(requests.post(f'{TikTok.API}/post/publish/video/init/', headers=TikTok._h(acc), json={
                'post_info': {'title': caption, 'privacy_level': privacy},
                'source_info': {'source': 'FILE_UPLOAD', 'video_size': size, 'chunk_size': size,
                                'total_chunk_count': 1}}, timeout=TIMEOUT), 'TikTok video')
            if (init.get('error') or {}).get('code') not in (None, 'ok'):
                raise PublishError(f"TikTok: {init['error'].get('message')}")
            data = init['data']
            up = requests.put(data['upload_url'], data=ctx.video.data, headers={
                'Content-Type': ctx.video.content_type or 'video/mp4',
                'Content-Range': f'bytes 0-{size - 1}/{size}'}, timeout=TIMEOUT * 5)
            if up.status_code >= 400:
                raise _err(up, 'TikTok upload')
            return data['publish_id'], ''
        if ctx.images:
            init = _check(requests.post(f'{TikTok.API}/post/publish/content/init/', headers=TikTok._h(acc), json={
                'post_info': {'title': (ctx.title or caption)[:90], 'description': caption, 'privacy_level': privacy},
                'source_info': {'source': 'PULL_FROM_URL', 'photo_cover_index': 0,
                                'photo_images': [i.url for i in ctx.images[:35]]},
                'post_mode': 'DIRECT_POST', 'media_type': 'PHOTO'}, timeout=TIMEOUT), 'TikTok photos')
            if (init.get('error') or {}).get('code') not in (None, 'ok'):
                raise PublishError(f"TikTok: {init['error'].get('message')}")
            return init['data']['publish_id'], ''
        raise PublishError('TikTok needs a video or photos.')


# ── LinkedIn company page ─────────────────────────────────────────────────────

def _li_escape(text):
    # LinkedIn's "little text" format reserves these characters
    for ch in '\\|{}@[]()<>#*_~':
        text = text.replace(ch, '\\' + ch)
    return text


class LinkedIn:
    fields = [('organization_id', 'Organization (company page) ID', False), ('access_token', 'Access token', True)]
    API = 'https://api.linkedin.com/rest'
    VERSION = '202502'

    @staticmethod
    def _h(acc, json_body=True):
        h = {'Authorization': f"Bearer {acc.secrets.get('access_token')}", 'LinkedIn-Version': LinkedIn.VERSION,
             'X-Restli-Protocol-Version': '2.0.0'}
        if json_body:
            h['Content-Type'] = 'application/json'
        return h

    @staticmethod
    def verify(acc):
        r = requests.get(f"{LinkedIn.API}/organizations/{acc.config.get('organization_id')}",
                         headers=LinkedIn._h(acc, False), timeout=TIMEOUT)
        return f"Page: {_check(r, 'LinkedIn').get('localizedName', '')}"

    @staticmethod
    def _owner(acc):
        return f"urn:li:organization:{acc.config.get('organization_id')}"

    @staticmethod
    def _upload_image(acc, img):
        d = _check(requests.post(f'{LinkedIn.API}/images?action=initializeUpload', headers=LinkedIn._h(acc), json={
            'initializeUploadRequest': {'owner': LinkedIn._owner(acc)}}, timeout=TIMEOUT), 'LinkedIn image')
        v = d['value']
        r = requests.put(v['uploadUrl'], data=img.data, headers={'Authorization': LinkedIn._h(acc)['Authorization']},
                         timeout=TIMEOUT * 2)
        if r.status_code >= 400:
            raise _err(r, 'LinkedIn image upload')
        return v['image']

    @staticmethod
    def _upload_video(acc, vid):
        size = len(vid.data)
        d = _check(requests.post(f'{LinkedIn.API}/videos?action=initializeUpload', headers=LinkedIn._h(acc), json={
            'initializeUploadRequest': {'owner': LinkedIn._owner(acc), 'fileSizeBytes': size,
                                        'uploadCaptions': False, 'uploadThumbnail': False}},
            timeout=TIMEOUT), 'LinkedIn video')
        v = d['value']
        etags = []
        for part in v['uploadInstructions']:
            r = requests.put(part['uploadUrl'], data=vid.data[part['firstByte']:part['lastByte'] + 1],
                             headers={'Authorization': LinkedIn._h(acc)['Authorization']}, timeout=TIMEOUT * 3)
            if r.status_code >= 400:
                raise _err(r, 'LinkedIn video upload')
            etags.append(r.headers.get('etag', ''))
        _check(requests.post(f'{LinkedIn.API}/videos?action=finalizeUpload', headers=LinkedIn._h(acc), json={
            'finalizeUploadRequest': {'video': v['video'], 'uploadToken': v.get('uploadToken', ''),
                                      'uploadedPartIds': etags}}, timeout=TIMEOUT), 'LinkedIn video finalize')
        return v['video']

    @staticmethod
    def publish(acc, ctx):
        body = {
            'author': LinkedIn._owner(acc),
            'commentary': _li_escape(ctx.text if (ctx.link and not ctx.images and not ctx.video) else ctx.text_with_link()),
            'visibility': 'PUBLIC',
            'distribution': {'feedDistribution': 'MAIN_FEED', 'targetEntities': [],
                             'thirdPartyDistributionChannels': []},
            'lifecycleState': 'PUBLISHED', 'isReshareDisabledByAuthor': False,
        }
        if ctx.video:
            body['content'] = {'media': {'id': LinkedIn._upload_video(acc, ctx.video), 'title': ctx.title or ''}}
        elif len(ctx.images) == 1:
            body['content'] = {'media': {'id': LinkedIn._upload_image(acc, ctx.images[0])}}
        elif ctx.images:
            body['content'] = {'multiImage': {'images': [{'id': LinkedIn._upload_image(acc, i)}
                                                         for i in ctx.images[:20]]}}
        elif ctx.link:
            body['content'] = {'article': {'source': ctx.link, 'title': ctx.title or ctx.link}}
        r = requests.post(f'{LinkedIn.API}/posts', headers=LinkedIn._h(acc), json=body, timeout=TIMEOUT)
        if r.status_code >= 400:
            raise _err(r, 'LinkedIn')
        urn = r.headers.get('x-restli-id', '')
        return urn, f'https://www.linkedin.com/feed/update/{urn}' if urn else ''


# ── YouTube ───────────────────────────────────────────────────────────────────

class YouTube:
    fields = [('client_id', 'OAuth client ID', True), ('client_secret', 'OAuth client secret', True),
              ('refresh_token', 'Refresh token', True), ('privacy', 'Privacy (public / unlisted / private)', False)]

    @staticmethod
    def _token(acc):
        s = acc.secrets
        r = requests.post('https://oauth2.googleapis.com/token', data={
            'client_id': s.get('client_id'), 'client_secret': s.get('client_secret'),
            'refresh_token': s.get('refresh_token'), 'grant_type': 'refresh_token'}, timeout=TIMEOUT)
        d = _check(r, 'YouTube sign-in')
        return d['access_token']

    @staticmethod
    def verify(acc):
        r = requests.get('https://www.googleapis.com/youtube/v3/channels', params={'part': 'snippet', 'mine': 'true'},
                         headers={'Authorization': f'Bearer {YouTube._token(acc)}'}, timeout=TIMEOUT)
        items = _check(r, 'YouTube').get('items') or []
        if items and acc.config.get('channel_id') != items[0].get('id'):
            acc.config['channel_id'] = items[0].get('id')   # to recognise our own replies
            if acc.pk:
                acc.save(update_fields=['config'])
        return f"Channel: {items[0]['snippet']['title']}" if items else 'Connected (no channel found)'

    @staticmethod
    def publish(acc, ctx):
        if not ctx.video:
            raise PublishError('YouTube needs a video.')
        token = YouTube._token(acc)
        meta = {'snippet': {'title': (ctx.title or ctx.text.split('\n')[0] or 'HuxNovel')[:100],
                            'description': ctx.text_with_link()[:5000], 'categoryId': '22'},
                'status': {'privacyStatus': acc.config.get('privacy') or 'public',
                           'selfDeclaredMadeForKids': False}}
        size = len(ctx.video.data)
        start = requests.post(
            'https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status',
            json=meta, headers={'Authorization': f'Bearer {token}', 'X-Upload-Content-Length': str(size),
                                'X-Upload-Content-Type': ctx.video.content_type or 'video/mp4'}, timeout=TIMEOUT)
        if start.status_code >= 400:
            raise _err(start, 'YouTube')
        up = requests.put(start.headers['Location'], data=ctx.video.data, headers={
            'Authorization': f'Bearer {token}', 'Content-Type': ctx.video.content_type or 'video/mp4'},
            timeout=TIMEOUT * 10)
        d = _check(up, 'YouTube upload')
        return d['id'], f"https://youtu.be/{d['id']}"


# ── Telegram channel ──────────────────────────────────────────────────────────

class Telegram:
    fields = [('chat_id', 'Channel (@username or -100… id)', False), ('bot_token', 'Bot token', True)]

    @staticmethod
    def _call(acc, method, **data):
        r = requests.post(f"https://api.telegram.org/bot{acc.secrets.get('bot_token')}/{method}", json=data,
                          timeout=TIMEOUT)
        d = _json(r)
        if not d.get('ok'):
            raise PublishError(f"Telegram: {d.get('description', r.status_code)}")
        return d['result']

    @staticmethod
    def verify(acc):
        c = Telegram._call(acc, 'getChat', chat_id=acc.config.get('chat_id'))
        return f"Channel: {c.get('title')}"

    @staticmethod
    def publish(acc, ctx):
        chat = acc.config.get('chat_id')
        text = ctx.text_with_link()
        caption = text if len(text) <= 1024 else ''
        if ctx.video:
            m = Telegram._call(acc, 'sendVideo', chat_id=chat, video=ctx.video.url, caption=caption)
        elif len(ctx.images) == 1:
            m = Telegram._call(acc, 'sendPhoto', chat_id=chat, photo=ctx.images[0].url, caption=caption)
        elif ctx.images:
            group = [{'type': 'photo', 'media': i.url} for i in ctx.images[:10]]
            group[0]['caption'] = caption
            m = Telegram._call(acc, 'sendMediaGroup', chat_id=chat, media=group)[0]
        else:
            m = Telegram._call(acc, 'sendMessage', chat_id=chat, text=text)
            caption = text
        if (ctx.video or ctx.images) and not caption:
            Telegram._call(acc, 'sendMessage', chat_id=chat, text=text)   # too long for a caption
        username = (m.get('chat') or {}).get('username')
        url = f"https://t.me/{username}/{m['message_id']}" if username else ''
        return str(m['message_id']), url


PUBLISHERS = {
    'facebook': Facebook, 'instagram': Instagram, 'threads': Threads, 'x': X,
    'tiktok': TikTok, 'linkedin': LinkedIn, 'youtube': YouTube, 'telegram': Telegram,
}
