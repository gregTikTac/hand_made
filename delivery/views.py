"""Public download and the «letter did not arrive» form."""

from django.db.models import F
from django.http import FileResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit

from delivery.models import DownloadLink
from delivery.services import hash_token, resend_to_email


def _client_ip(request):
    return request.META.get("REMOTE_ADDR") or None


def _open_link(link: DownloadLink, request):
    storage = link.watermarked.storage
    name = link.watermarked.name
    # S3 storage builds a short-lived signed URL. Local storage has no public address.
    if storage.__class__.__name__ == "S3Storage":
        return HttpResponseRedirect(storage.url(name))
    handle = storage.open(name, "rb")
    filename = f"{link.label}.pdf" if not link.label.lower().endswith(".pdf") else link.label
    return FileResponse(handle, as_attachment=True, filename=filename)


@ratelimit(key="ip", rate="30/m", method="GET", block=False)
def download(request, token: str):
    if getattr(request, "limited", False):
        return render(request, "delivery/download.html", {"state": "limited"}, status=429)
    link = DownloadLink.objects.filter(token_hash=hash_token(token)).first()
    now = timezone.now()
    if link is None or link.revoked or link.expires_at <= now:
        return render(request, "delivery/download.html", {"state": "dead"}, status=404)
    updated = DownloadLink.objects.filter(
        pk=link.pk,
        revoked=False,
        expires_at__gt=now,
        download_count__lt=F("max_downloads"),
    ).update(download_count=F("download_count") + 1, last_ip=_client_ip(request))
    if not updated:
        return render(request, "delivery/download.html", {"state": "limit"}, status=410)
    return _open_link(link, request)


@require_http_methods(["GET", "POST"])
@ratelimit(key="ip", rate="5/h", method="POST", block=False)
def resend(request):
    sent = False
    if request.method == "POST" and not getattr(request, "limited", False):
        email = (request.POST.get("email") or "").strip()
        if email:
            resend_to_email(email)
            sent = True
    return render(
        request,
        "delivery/resend.html",
        {"sent": sent, "limited": getattr(request, "limited", False)},
    )
