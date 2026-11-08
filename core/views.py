from django.db import connection
from django.db.utils import DatabaseError
from django.http import JsonResponse


def healthz(request):
    """For the load balancer, uptime monitor and the deploy script.
    200 only if the app can really reach its database."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "error", "database": "unreachable"}, status=503)
    return JsonResponse({"status": "ok"})
