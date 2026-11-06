"""Archivos cuyo nombre cambia en cada publicación: se busca el enlace en la página del organismo.

Solo se aceptan enlaces al mismo host de la página (o a los hosts que se indiquen), por HTTPS.
"""

import re
from urllib.parse import urljoin, urlparse


def buscar(descargar, pagina: str, patron: str, hosts: tuple[str, ...] = ()) -> str:
    """Primer enlace de la página cuyo href cumple `patron` (expresión regular sobre el href)."""
    html = descargar(pagina, minimo=2_000).decode("utf-8", "replace")
    permitidos = {urlparse(pagina).hostname, *hosts}
    for href in re.findall(r'href="([^"]+)"', html):
        href = href.replace("&amp;", "&")
        if not re.search(patron, href):
            continue
        url = urljoin(pagina, href)
        u = urlparse(url)
        if u.scheme == "https" and u.hostname in permitidos:
            return url
    raise ValueError(f"No encontré en {pagina} un enlace que cumpla {patron!r}.")
