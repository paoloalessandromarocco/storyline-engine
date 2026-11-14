#!/usr/bin/env python3
"""
Adds a client-side password gate to the <div class="page-body">...</div>
block of a static HTML page on this site.

How it works: the real content of that block is encrypted once, here, with
AES-256-GCM (key derived from a password via PBKDF2-HMAC-SHA256, 250k
iterations) and replaced in the shipped HTML with a small lock panel plus a
vanilla-JS script (Web Crypto API) that re-derives the key and decrypts the
content in the visitor's browser, in-place, when the right code is entered.
No server, no build step at request time, no external JS library. Header,
nav, footer and scripts outside page-body are untouched and keep working.

Honest limits (tell Paolo, don't just assume he remembers): this stops
casual browsing, scraping and view-source — it does not stop someone who
has the code from sharing it, nor a determined attacker running an offline
brute-force against the ciphertext blob with unlimited time. It is not
meant to protect real trade secrets, only to add friction and a manual
distribution step.

Usage:
    python3 scripts/gate_protect.py PASSWORD file1.html [file2.html ...]

Run only on the ORIGINAL (ungated) file. Running it twice on an already
gated file will encrypt the lock panel itself instead of the real content.
To rotate the password: restore the page from git history to the pre-gate
commit, then re-run with the new password.
"""
import sys, re, json, base64, secrets
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ITERATIONS = 250_000
PAGE_BODY_RE = re.compile(
    r'<div class="page-body">(.*?)</div><!-- /page-body -->',
    re.DOTALL,
)

GATE_TEXT = {
    "it": {
        "notice": "Questa pagina contiene le specifiche tecniche complete ed è disponibile su richiesta.",
        "howto": 'Per ricevere il codice d’accesso scrivi a <a href="mailto:paolo.marocco2000@gmail.com" class="about-link">paolo.marocco2000@gmail.com</a>.',
        "placeholder": "Codice d’accesso",
        "button": "Sblocca",
        "error": "Codice non valido.",
    },
    "en": {
        "notice": "This page contains the full technical specification and is available on request.",
        "howto": 'To receive the access code, email <a href="mailto:paolo.marocco2000@gmail.com" class="about-link">paolo.marocco2000@gmail.com</a>.',
        "placeholder": "Access code",
        "button": "Unlock",
        "error": "Invalid code.",
    },
}


def detect_lang(html: str) -> str:
    m = re.search(r'<html lang="([a-z]{2})"', html)
    lang = m.group(1) if m else "en"
    return lang if lang in GATE_TEXT else "en"


def b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def encrypt(plaintext: bytes, password: str):
    salt = secrets.token_bytes(16)
    iv = secrets.token_bytes(12)
    key = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS
    ).derive(password.encode("utf-8"))
    ct = AESGCM(key).encrypt(iv, plaintext, None)
    return b64(salt), b64(iv), b64(ct)


def build_gate_block(lang: str, salt_b64: str, iv_b64: str, ct_b64: str) -> str:
    t = GATE_TEXT[lang]
    data = json.dumps({"salt": salt_b64, "iv": iv_b64, "ct": ct_b64})
    return f'''<div class="page-body" id="page-body">
      <style>
        #gate-panel {{ max-width: 32rem; margin: 2rem 0; }}
        #gate-panel .gate-row {{ display: flex; gap: 0.6rem; margin-top: 1.2rem; flex-wrap: wrap; }}
        #gate-panel input[type="password"] {{
          font-family: inherit; font-size: 1rem; padding: 0.5rem 0.7rem;
          border: 1px solid var(--burgundy, #6B2737); background: transparent;
          color: var(--burgundy, #6B2737); flex: 1 1 14rem;
        }}
        #gate-panel button {{
          font-family: inherit; font-size: 0.95rem; padding: 0.5rem 1.1rem;
          border: 1px solid #002FA7; background: #002FA7; color: #F7F2E6;
          cursor: pointer;
        }}
        #gate-panel button:hover {{ background: #001D6C; border-color: #001D6C; }}
        #gate-panel button:disabled {{ opacity: 0.5; cursor: default; }}
        #gate-error {{ color: var(--burgundy, #6B2737); margin-top: 0.8rem; }}
      </style>
      <div id="gate-panel">
        <p class="post-text">{t['notice']}</p>
        <p class="post-text">{t['howto']}</p>
        <form id="gate-form" autocomplete="off">
          <div class="gate-row">
            <input type="password" id="gate-code" placeholder="{t['placeholder']}" autocomplete="off">
            <button type="submit">{t['button']}</button>
          </div>
        </form>
        <p id="gate-error" style="display:none;">{t['error']}</p>
      </div>
    </div><!-- /page-body -->
    <script id="gate-data" type="application/json">{data}</script>
    <script>
    (function () {{
      var ITERATIONS = {ITERATIONS};
      function b64d(s) {{
        var bin = atob(s), arr = new Uint8Array(bin.length);
        for (var i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
        return arr;
      }}
      async function deriveKey(pw, saltBytes) {{
        var enc = new TextEncoder();
        var km = await crypto.subtle.importKey('raw', enc.encode(pw), {{ name: 'PBKDF2' }}, false, ['deriveKey']);
        return crypto.subtle.deriveKey(
          {{ name: 'PBKDF2', salt: saltBytes, iterations: ITERATIONS, hash: 'SHA-256' }},
          km, {{ name: 'AES-GCM', length: 256 }}, false, ['decrypt']
        );
      }}
      async function tryUnlock(pw) {{
        var data = JSON.parse(document.getElementById('gate-data').textContent);
        var salt = b64d(data.salt), iv = b64d(data.iv), ct = b64d(data.ct);
        var key = await deriveKey(pw, salt);
        var buf = await crypto.subtle.decrypt({{ name: 'AES-GCM', iv: iv }}, key, ct);
        return new TextDecoder().decode(buf);
      }}
      var cacheKey = 'gate_' + location.pathname;
      function reveal(html) {{
        document.getElementById('page-body').innerHTML = html;
      }}
      var cached;
      try {{ cached = sessionStorage.getItem(cacheKey); }} catch (e) {{}}
      if (cached) {{ reveal(cached); return; }}
      var form = document.getElementById('gate-form');
      var input = document.getElementById('gate-code');
      var err = document.getElementById('gate-error');
      form.addEventListener('submit', function (ev) {{
        ev.preventDefault();
        err.style.display = 'none';
        tryUnlock(input.value).then(function (html) {{
          try {{ sessionStorage.setItem(cacheKey, html); }} catch (e) {{}}
          reveal(html);
        }}).catch(function () {{
          err.style.display = 'block';
        }});
      }});
    }})();
    </script>'''


def gate_file(path: str, password: str) -> None:
    with open(path, "r", encoding="utf-8") as fh:
        html = fh.read()
    matches = PAGE_BODY_RE.findall(html)
    if len(matches) != 1:
        raise SystemExit(f"{path}: expected exactly 1 page-body block, found {len(matches)}")
    lang = detect_lang(html)
    m = PAGE_BODY_RE.search(html)
    real_content = m.group(1)
    salt_b64, iv_b64, ct_b64 = encrypt(real_content.encode("utf-8"), password)
    gate_block = build_gate_block(lang, salt_b64, iv_b64, ct_b64)
    new_html = html[: m.start()] + gate_block + html[m.end():]
    if 'name="robots"' not in new_html:
        new_html = new_html.replace(
            "<head>", '<head>\n  <meta name="robots" content="noindex">', 1
        )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new_html)
    print(f"gated {path}  (lang={lang}, original content bytes={len(real_content)})")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit("usage: gate_protect.py PASSWORD file1.html [file2.html ...]")
    pw = sys.argv[1]
    for p in sys.argv[2:]:
        gate_file(p, pw)
