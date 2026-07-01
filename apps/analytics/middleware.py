import threading
import logging

logger = logging.getLogger(__name__)

_SKIP_PREFIXES = (
    '/admin/',
    '/api/schema/',
    '/api/docs/',
    '/static/',
    '/media/',
    '/favicon',
    '/robots.txt',
    '/sitemap',
)

_SKIP_EXTENSIONS = (
    '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg',
    '.ico', '.woff', '.woff2', '.ttf', '.map', '.webp',
)

_geoip_reader = None
_geoip_lock   = threading.Lock()


def _get_geoip_reader():
    global _geoip_reader
    if _geoip_reader is not None:
        return _geoip_reader
    with _geoip_lock:
        if _geoip_reader is not None:
            return _geoip_reader
        try:
            from django.conf import settings
            import geoip2.database
            db_path = getattr(settings, 'GEOIP_PATH', None)
            if db_path:
                import os
                mmdb = os.path.join(db_path, 'GeoLite2-City.mmdb')
                if os.path.exists(mmdb):
                    _geoip_reader = geoip2.database.Reader(mmdb)
                    logger.info('GeoIP2 reader loaded from %s', mmdb)
                else:
                    logger.warning('GeoIP2 DB not found at %s — geo lookup disabled', mmdb)
        except Exception as e:
            logger.warning('GeoIP2 init failed: %s', e)
    return _geoip_reader


def _get_client_ip(request):
    try:
        from ipware import get_client_ip
        ip, _ = get_client_ip(request)
        return ip
    except Exception:
        for header in ('HTTP_X_FORWARDED_FOR', 'HTTP_X_REAL_IP', 'REMOTE_ADDR'):
            ip = request.META.get(header, '').split(',')[0].strip()
            if ip:
                return ip
    return None


def _parse_device(ua_string):
    try:
        import user_agents
        ua = user_agents.parse(ua_string or '')
        if ua.is_bot:
            return 'bot', ua.browser.family, ua.os.family
        if ua.is_mobile:
            return 'mobile', ua.browser.family, ua.os.family
        if ua.is_tablet:
            return 'tablet', ua.browser.family, ua.os.family
        return 'desktop', ua.browser.family, ua.os.family
    except Exception:
        return '', '', ''


def _geo_lookup(ip):
    reader = _get_geoip_reader()
    if not reader or not ip:
        return '', '', ''
    try:
        r = reader.city(ip)
        return (
            r.country.name or '',
            r.country.iso_code or '',
            r.city.name or '',
        )
    except Exception:
        return '', '', ''


def _record(ip, path, referrer, device_type, browser, os_name,
            country, country_code, city, user_id):
    try:
        from apps.analytics.models import PageVisit
        PageVisit.objects.create(
            ip_address   = ip,
            path         = path[:500],
            referrer     = (referrer or '')[:500],
            device_type  = device_type,
            browser      = (browser or '')[:80],
            os           = (os_name or '')[:80],
            country      = country,
            country_code = country_code,
            city         = city,
            user_id      = user_id,
        )
    except Exception as e:
        logger.debug('Analytics record error: %s', e)


class AnalyticsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        try:
            path = request.path
            if any(path.startswith(p) for p in _SKIP_PREFIXES):
                return response
            if any(path.endswith(ext) for ext in _SKIP_EXTENSIONS):
                return response
            if response.status_code in (301, 302, 304):
                return response

            ip          = _get_client_ip(request)
            ua_string   = request.META.get('HTTP_USER_AGENT', '')
            referrer    = request.META.get('HTTP_REFERER', '')
            user_id     = request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None

            device_type, browser, os_name = _parse_device(ua_string)
            if device_type == 'bot':
                return response

            country, country_code, city = _geo_lookup(ip)

            t = threading.Thread(
                target=_record,
                args=(ip, path, referrer, device_type, browser, os_name,
                      country, country_code, city, user_id),
                daemon=True,
            )
            t.start()

        except Exception as e:
            logger.debug('AnalyticsMiddleware error: %s', e)

        return response
