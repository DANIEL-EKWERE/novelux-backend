"""Reading back from the networks: post numbers, follower counts, comments,
and replying to comments.

Each platform class may provide:
  metrics(acc, target)        → {views, likes, comments, shares, reach, …}
  followers(acc)              → int
  comments(acc, target)       → [{id, parent_id, name, handle, text, at, url}]
  reply(acc, comment, text)   → (external_id, url)

Missing methods mean the network doesn't allow it (e.g. TikTok comments).
"""
from urllib.parse import quote

import requests
from django.utils.dateparse import parse_datetime

from .publishers import (GRAPH, THREADS, Instagram as _Instagram, TIMEOUT, LinkedIn as _LinkedIn, PublishError, Telegram as _Telegram,
                         TikTok as _TikTok, X as _X, YouTube as _YouTube, _check, _json)


class NotSupported(Exception):
    pass


def _dt(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        from datetime import datetime, timezone
        return datetime.fromtimestamp(value / 1000 if value > 1e11 else value, tz=timezone.utc)
    v = str(value).replace('+0000', '+00:00')
    return parse_datetime(v)


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


# ── Facebook ──────────────────────────────────────────────────────────────────

class Facebook:
    @staticmethod
    def metrics(acc, t):
        token = acc.secrets.get('page_token')
        d = _check(requests.get(f'{GRAPH}/{t.external_id}', params={
            'fields': 'shares,comments.summary(true).limit(0),reactions.summary(true).limit(0)',
            'access_token': token}, timeout=TIMEOUT), 'Facebook')
        out = {'likes': _int((d.get('reactions') or {}).get('summary', {}).get('total_count')),
               'comments': _int((d.get('comments') or {}).get('summary', {}).get('total_count')),
               'shares': _int((d.get('shares') or {}).get('count'))}
        ins = requests.get(f'{GRAPH}/{t.external_id}/insights', params={
            'metric': 'post_impressions,post_impressions_unique', 'access_token': token}, timeout=TIMEOUT)
        for m in (_json(ins).get('data') or []) if ins.status_code < 400 else []:
            val = _int((m.get('values') or [{}])[0].get('value'))
            out['impressions' if m['name'] == 'post_impressions' else 'reach'] = val
        return out

    @staticmethod
    def followers(acc):
        d = _check(requests.get(f"{GRAPH}/{acc.config.get('page_id')}", params={
            'fields': 'followers_count,fan_count', 'access_token': acc.secrets.get('page_token')}, timeout=TIMEOUT),
            'Facebook')
        return _int(d.get('followers_count') or d.get('fan_count'))

    @staticmethod
    def comments(acc, t):
        d = _check(requests.get(f'{GRAPH}/{t.external_id}/comments', params={
            'fields': 'id,from,message,created_time,permalink_url,parent{id}', 'filter': 'stream',
            'order': 'reverse_chronological', 'limit': 100, 'access_token': acc.secrets.get('page_token')},
            timeout=TIMEOUT), 'Facebook comments')
        page_id = str(acc.config.get('page_id'))
        return [{'id': c['id'], 'parent_id': (c.get('parent') or {}).get('id'),
                 'name': (c.get('from') or {}).get('name', 'Facebook user'), 'handle': '',
                 'text': c.get('message', ''), 'at': _dt(c.get('created_time')), 'url': c.get('permalink_url', ''),
                 'ours': str((c.get('from') or {}).get('id')) == page_id} for c in d.get('data', [])]

    @staticmethod
    def reply(acc, comment, text):
        d = _check(requests.post(f'{GRAPH}/{comment.external_id}/comments', data={
            'message': text, 'access_token': acc.secrets.get('page_token')}, timeout=TIMEOUT), 'Facebook reply')
        return d['id'], ''


# ── Instagram ─────────────────────────────────────────────────────────────────

class Instagram:
    @staticmethod
    def metrics(acc, t):
        _Instagram.refresh(acc)
        token = acc.secrets.get('access_token')
        d = _check(requests.get(f'{_Instagram.base(acc)}/{t.external_id}', params={
            'fields': 'like_count,comments_count,media_type', 'access_token': token}, timeout=TIMEOUT), 'Instagram')
        out = {'likes': _int(d.get('like_count')), 'comments': _int(d.get('comments_count'))}
        # Available metrics differ by media type — ask for a set, fall back to reach
        for metric_set in ('reach,saved,shares,views', 'reach,saved', 'reach'):
            r = requests.get(f'{_Instagram.base(acc)}/{t.external_id}/insights', params={'metric': metric_set, 'access_token': token},
                             timeout=TIMEOUT)
            if r.status_code < 400:
                for m in _json(r).get('data') or []:
                    out[{'saved': 'saves'}.get(m['name'], m['name'])] = _int((m.get('values') or [{}])[0].get('value'))
                break
        return out

    @staticmethod
    def followers(acc):
        d = _check(requests.get(f"{_Instagram.base(acc)}/{_Instagram.user_id(acc)}", params={
            'fields': 'followers_count', 'access_token': acc.secrets.get('access_token')}, timeout=TIMEOUT), 'Instagram')
        return _int(d.get('followers_count'))

    @staticmethod
    def comments(acc, t):
        d = _check(requests.get(f'{_Instagram.base(acc)}/{t.external_id}/comments', params={
            'fields': 'id,text,username,timestamp,replies{id,text,username,timestamp}', 'limit': 100,
            'access_token': acc.secrets.get('access_token')}, timeout=TIMEOUT), 'Instagram comments')
        me = (acc.handle or '').lstrip('@')
        out = []
        for c in d.get('data', []):
            out.append({'id': c['id'], 'parent_id': None, 'name': c.get('username', ''), 'handle': c.get('username', ''),
                        'text': c.get('text', ''), 'at': _dt(c.get('timestamp')), 'url': '',
                        'ours': c.get('username') == me})
            for r in (c.get('replies') or {}).get('data', []):
                out.append({'id': r['id'], 'parent_id': c['id'], 'name': r.get('username', ''),
                            'handle': r.get('username', ''), 'text': r.get('text', ''), 'at': _dt(r.get('timestamp')),
                            'url': '', 'ours': r.get('username') == me})
        return out

    @staticmethod
    def reply(acc, comment, text):
        d = _check(requests.post(f'{_Instagram.base(acc)}/{comment.external_id}/replies', data={
            'message': text, 'access_token': acc.secrets.get('access_token')}, timeout=TIMEOUT), 'Instagram reply')
        return d['id'], ''


# ── Threads ───────────────────────────────────────────────────────────────────

class Threads:
    @staticmethod
    def metrics(acc, t):
        d = _check(requests.get(f'{THREADS}/{t.external_id}/insights', params={
            'metric': 'views,likes,replies,reposts,quotes,shares', 'access_token': acc.secrets.get('access_token')},
            timeout=TIMEOUT), 'Threads')
        out = {}
        for m in d.get('data') or []:
            val = (m.get('values') or [{}])[0].get('value') if m.get('values') else (m.get('total_value') or {}).get('value')
            out[{'replies': 'comments'}.get(m['name'], m['name'])] = _int(val)
        return out

    @staticmethod
    def followers(acc):
        d = _check(requests.get(f"{THREADS}/{acc.config.get('user_id')}/threads_insights", params={
            'metric': 'followers_count', 'access_token': acc.secrets.get('access_token')}, timeout=TIMEOUT), 'Threads')
        for m in d.get('data') or []:
            return _int((m.get('total_value') or {}).get('value'))
        return 0

    @staticmethod
    def comments(acc, t):
        d = _check(requests.get(f'{THREADS}/{t.external_id}/replies', params={
            'fields': 'id,text,username,timestamp,permalink', 'access_token': acc.secrets.get('access_token')},
            timeout=TIMEOUT), 'Threads replies')
        me = (acc.handle or '').lstrip('@')
        return [{'id': c['id'], 'parent_id': None, 'name': c.get('username', ''), 'handle': c.get('username', ''),
                 'text': c.get('text', ''), 'at': _dt(c.get('timestamp')), 'url': c.get('permalink', ''),
                 'ours': c.get('username') == me} for c in d.get('data', [])]

    @staticmethod
    def reply(acc, comment, text):
        uid, token = acc.config.get('user_id'), acc.secrets.get('access_token')
        c = _check(requests.post(f'{THREADS}/{uid}/threads', data={
            'media_type': 'TEXT', 'text': text, 'reply_to_id': comment.external_id, 'access_token': token},
            timeout=TIMEOUT), 'Threads reply')
        d = _check(requests.post(f'{THREADS}/{uid}/threads_publish', data={
            'creation_id': c['id'], 'access_token': token}, timeout=TIMEOUT), 'Threads reply')
        return d['id'], ''


# ── X ─────────────────────────────────────────────────────────────────────────

class X:
    @staticmethod
    def metrics(acc, t):
        d = _check(_X._session(acc).get(f'https://api.x.com/2/tweets/{t.external_id}',
                                        params={'tweet.fields': 'public_metrics'}, timeout=TIMEOUT), 'X')
        m = (d.get('data') or {}).get('public_metrics') or {}
        return {'views': _int(m.get('impression_count')), 'likes': _int(m.get('like_count')),
                'comments': _int(m.get('reply_count')), 'shares': _int(m.get('retweet_count')),
                'quotes': _int(m.get('quote_count')), 'saves': _int(m.get('bookmark_count'))}

    @staticmethod
    def followers(acc):
        d = _check(_X._session(acc).get('https://api.x.com/2/users/me', params={'user.fields': 'public_metrics'},
                                        timeout=TIMEOUT), 'X')
        return _int(((d.get('data') or {}).get('public_metrics') or {}).get('followers_count'))

    @staticmethod
    def comments(acc, t):
        # Reading replies needs an X plan that includes search
        r = _X._session(acc).get('https://api.x.com/2/tweets/search/recent', params={
            'query': f'conversation_id:{t.external_id}', 'max_results': 100,
            'tweet.fields': 'author_id,created_at,in_reply_to_user_id,referenced_tweets',
            'expansions': 'author_id', 'user.fields': 'username,name'}, timeout=TIMEOUT)
        d = _check(r, 'X replies')
        users = {u['id']: u for u in (d.get('includes') or {}).get('users', [])}
        me = (acc.handle or '').lstrip('@')
        out = []
        for tw in d.get('data', []):
            u = users.get(tw.get('author_id'), {})
            parent = next((x['id'] for x in tw.get('referenced_tweets', []) if x.get('type') == 'replied_to'), None)
            out.append({'id': tw['id'], 'parent_id': None if parent == t.external_id else parent,
                        'name': u.get('name', ''), 'handle': u.get('username', ''), 'text': tw.get('text', ''),
                        'at': _dt(tw.get('created_at')), 'url': f"https://x.com/i/web/status/{tw['id']}",
                        'ours': u.get('username') == me})
        return out

    @staticmethod
    def reply(acc, comment, text):
        d = _check(_X._session(acc).post('https://api.x.com/2/tweets', json={
            'text': text, 'reply': {'in_reply_to_tweet_id': comment.external_id}}, timeout=TIMEOUT), 'X reply')
        tid = (d.get('data') or {}).get('id', '')
        return tid, f'https://x.com/i/web/status/{tid}'


# ── TikTok (numbers only — TikTok has no comments API) ───────────────────────

class TikTok:
    @staticmethod
    def metrics(acc, t):
        _TikTok.refresh(acc)
        video_id = (t.metrics or {}).get('video_id')
        if not video_id:
            # We only get a publish id when posting; ask TikTok for the video id
            s = _check(requests.post(f'{_TikTok.API}/post/publish/status/fetch/', headers=_TikTok._h(acc),
                                     json={'publish_id': t.external_id}, timeout=TIMEOUT), 'TikTok status')
            ids = (s.get('data') or {}).get('publicaly_available_post_id') or []
            if not ids:
                return {'status': (s.get('data') or {}).get('status', 'processing')}
            video_id = str(ids[0])
        d = _check(requests.post(f'{_TikTok.API}/video/query/?fields=id,view_count,like_count,comment_count,share_count,share_url',
                                 headers=_TikTok._h(acc), json={'filters': {'video_ids': [video_id]}},
                                 timeout=TIMEOUT), 'TikTok')
        v = ((d.get('data') or {}).get('videos') or [{}])[0]
        if v.get('share_url') and not t.url:
            t.url = v['share_url']
        return {'video_id': video_id, 'views': _int(v.get('view_count')), 'likes': _int(v.get('like_count')),
                'comments': _int(v.get('comment_count')), 'shares': _int(v.get('share_count'))}

    @staticmethod
    def followers(acc):
        _TikTok.refresh(acc)
        d = _check(requests.get(f'{_TikTok.API}/user/info/', params={'fields': 'follower_count'},
                                headers=_TikTok._h(acc), timeout=TIMEOUT), 'TikTok')
        return _int(((d.get('data') or {}).get('user') or {}).get('follower_count'))


# ── LinkedIn ──────────────────────────────────────────────────────────────────

class LinkedIn:
    @staticmethod
    def metrics(acc, t):
        urn = t.external_id
        kind = 'ugcPosts' if ':ugcPost:' in urn else 'shares'
        org = quote(_LinkedIn._owner(acc), safe='')
        r = requests.get(f'{_LinkedIn.API}/organizationalEntityShareStatistics?q=organizationalEntity'
                         f'&organizationalEntity={org}&{kind}=List({quote(urn, safe="")})',
                         headers=_LinkedIn._h(acc, False), timeout=TIMEOUT)
        d = _check(r, 'LinkedIn')
        s = ((d.get('elements') or [{}])[0].get('totalShareStatistics')) or {}
        return {'views': _int(s.get('impressionCount')), 'reach': _int(s.get('uniqueImpressionsCount')),
                'likes': _int(s.get('likeCount')), 'comments': _int(s.get('commentCount')),
                'shares': _int(s.get('shareCount')), 'clicks': _int(s.get('clickCount'))}

    @staticmethod
    def followers(acc):
        r = requests.get(f"{_LinkedIn.API}/networkSizes/{quote(_LinkedIn._owner(acc), safe='')}",
                         params={'edgeType': 'COMPANY_FOLLOWED_BY_MEMBER'}, headers=_LinkedIn._h(acc, False),
                         timeout=TIMEOUT)
        return _int(_check(r, 'LinkedIn').get('firstDegreeSize'))

    @staticmethod
    def comments(acc, t):
        r = requests.get(f"{_LinkedIn.API}/socialActions/{quote(t.external_id, safe='')}/comments",
                         headers=_LinkedIn._h(acc, False), timeout=TIMEOUT)
        d = _check(r, 'LinkedIn comments')
        org = _LinkedIn._owner(acc)
        out = []
        for c in d.get('elements', []):
            cid = c.get('$URN') or c.get('commentUrn') or str(c.get('id'))
            out.append({'id': cid, 'parent_id': c.get('parentComment'), 'name': 'LinkedIn member', 'handle': '',
                        'text': (c.get('message') or {}).get('text', ''),
                        'at': _dt((c.get('created') or {}).get('time')), 'url': '',
                        'ours': c.get('actor') == org})
        return out

    @staticmethod
    def reply(acc, comment, text):
        post_urn = comment.target.external_id
        body = {'actor': _LinkedIn._owner(acc), 'object': post_urn, 'message': {'text': text},
                'parentComment': comment.external_id}
        r = requests.post(f"{_LinkedIn.API}/socialActions/{quote(post_urn, safe='')}/comments",
                          headers=_LinkedIn._h(acc), json=body, timeout=TIMEOUT)
        if r.status_code >= 400:
            raise PublishError(f'LinkedIn reply: {r.status_code} — {r.text[:200]}')
        return r.headers.get('x-restli-id', ''), ''


# ── YouTube ───────────────────────────────────────────────────────────────────

class YouTube:
    @staticmethod
    def _get(acc, path, **params):
        r = requests.get(f'https://www.googleapis.com/youtube/v3/{path}', params=params,
                         headers={'Authorization': f'Bearer {_YouTube._token(acc)}'}, timeout=TIMEOUT)
        return _check(r, 'YouTube')

    @staticmethod
    def metrics(acc, t):
        items = YouTube._get(acc, 'videos', part='statistics', id=t.external_id).get('items') or [{}]
        s = items[0].get('statistics') or {}
        return {'views': _int(s.get('viewCount')), 'likes': _int(s.get('likeCount')),
                'comments': _int(s.get('commentCount'))}

    @staticmethod
    def followers(acc):
        items = YouTube._get(acc, 'channels', part='statistics', mine='true').get('items') or [{}]
        return _int((items[0].get('statistics') or {}).get('subscriberCount'))

    @staticmethod
    def comments(acc, t):
        d = YouTube._get(acc, 'commentThreads', part='snippet,replies', videoId=t.external_id, maxResults=100,
                         order='time')
        out = []
        for th in d.get('items', []):
            top = th['snippet']['topLevelComment']
            s = top['snippet']
            out.append({'id': top['id'], 'parent_id': None, 'name': s.get('authorDisplayName', ''), 'handle': '',
                        'text': s.get('textOriginal', ''), 'at': _dt(s.get('publishedAt')),
                        'url': f"https://www.youtube.com/watch?v={t.external_id}&lc={top['id']}",
                        'ours': s.get('authorChannelId', {}).get('value') == acc.config.get('channel_id')})
            for rp in (th.get('replies') or {}).get('comments', []):
                rs = rp['snippet']
                out.append({'id': rp['id'], 'parent_id': top['id'], 'name': rs.get('authorDisplayName', ''),
                            'handle': '', 'text': rs.get('textOriginal', ''), 'at': _dt(rs.get('publishedAt')),
                            'url': '', 'ours': rs.get('authorChannelId', {}).get('value') == acc.config.get('channel_id')})
        return out

    @staticmethod
    def reply(acc, comment, text):
        parent = comment.parent.external_id if comment.parent_id and not comment.parent.is_ours else comment.external_id
        r = requests.post('https://www.googleapis.com/youtube/v3/comments?part=snippet',
                          json={'snippet': {'parentId': parent, 'textOriginal': text}},
                          headers={'Authorization': f'Bearer {_YouTube._token(acc)}'}, timeout=TIMEOUT)
        return _check(r, 'YouTube reply')['id'], ''


# ── Telegram (followers; comments via the channel's discussion group) ───────

class Telegram:
    @staticmethod
    def followers(acc):
        return _int(_Telegram._call(acc, 'getChatMemberCount', chat_id=acc.config.get('chat_id')))

    @staticmethod
    def updates(acc):
        """New messages the bot can see. Comments are messages in the channel's
        discussion group that reply to one of our (auto-forwarded) posts."""
        offset = _int(acc.config.get('update_offset'))
        res = _Telegram._call(acc, 'getUpdates', offset=offset or None, timeout=0,
                              allowed_updates=['message'])
        out = []
        for u in res:
            offset = max(offset, u['update_id'] + 1)
            m = u.get('message') or {}
            rt = m.get('reply_to_message') or {}
            if not m.get('text') or not rt:
                continue
            # The post being commented on is the auto-forward of our channel post
            origin = rt.get('forward_origin') or {}
            channel_msg = origin.get('message_id') or rt.get('forward_from_message_id')
            frm = m.get('from') or {}
            out.append({'id': f"{m['chat']['id']}:{m['message_id']}", 'channel_msg': str(channel_msg or ''),
                        'reply_to': f"{m['chat']['id']}:{rt['message_id']}",
                        'name': ' '.join(x for x in (frm.get('first_name'), frm.get('last_name')) if x) or 'Telegram user',
                        'handle': frm.get('username', ''), 'text': m.get('text', ''), 'at': _dt(m.get('date')),
                        'url': '', 'ours': bool(frm.get('is_bot'))})
        acc.config['update_offset'] = offset
        acc.save(update_fields=['config'])
        return out

    @staticmethod
    def reply(acc, comment, text):
        chat_id, msg_id = comment.external_id.split(':', 1)
        m = _Telegram._call(acc, 'sendMessage', chat_id=int(chat_id), text=text, reply_to_message_id=int(msg_id))
        return f"{chat_id}:{m['message_id']}", ''


INSIGHTS = {'facebook': Facebook, 'instagram': Instagram, 'threads': Threads, 'x': X, 'tiktok': TikTok,
            'linkedin': LinkedIn, 'youtube': YouTube, 'telegram': Telegram}


def supports(platform, what):
    return hasattr(INSIGHTS.get(platform), what)
