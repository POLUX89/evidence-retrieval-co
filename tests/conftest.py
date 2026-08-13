"""Synthetic Drupal-like fixtures mirroring the cached pages' structure.

All text and URLs are invented — no scraped ColombiaCheck content lands in
this public repo (Datasheet stance). The DOM skeleton mirrors the real theme:
wrapper `div.row.<verdict>.text-articulos`, a `div.col-12.col-md-9` column
holding an attribute-less prose `<div>`, and boilerplate (nav, share block,
related articles, footer) OUTSIDE the wrapper.
"""

import pytest

SYNTH_ARTICLE = """<html><body>
<nav class="Navigation-menu">
  <a class="Navigation-menu-social-icon" href="http://t.me/SynthOrg">Telegram</a>
  <a class="Navigation-menu-social-icon" href="https://wa.me/570000000?text=Hola">WhatsApp</a>
  <a href="https://colombiacheck.com/investigaciones">Nav link</a>
</nav>
<div id="99" class="articulos"><div class="container">
<div class="row falso text-articulos">
  <h2>Synthetic headline for tests</h2>
  <h3>Synthetic standfirst</h3>
  <div class="col-12 col-md-9">
    <div>
      <p>Invented paragraph citing
      <a href="https://www.dane.gov.co/files/invented-report.pdf">a DANE file</a>,
      <a href="https://twitter.com/synthuser/status/1">a tweet</a>,
      <a href="https://archive.ph/AbCdE">an archived page</a>,
      <a href="https://t.me/synthchannel/5">a Telegram channel post</a> and
      <a href="https://www.instagram.com/p/synthpost/">an Instagram post</a>.</p>
      <p>Second invented paragraph with a relative
      <a href="/chequeos/otro-chequeo-inventado">internal link</a> and residue:
      <a href="https://www.facebook.com/sharer/sharer.php?u=https%3A%2F%2Fexample.test">share</a>
      <a href="https://twitter.com/intent/tweet?text=x">tweet intent</a>
      <a href="mailto:?subject=x&amp;body=y">mail</a>
      <a href="whatsapp://send?text=x">wa</a>
      <a href="https://t.me/share/url?url=x">tg share</a>.</p>
    </div>
  </div>
  <div class="col-12 col-md-3 col-relacionados">
    <a href="/chequeos/relacionado-inventado">related article</a>
  </div>
</div>
</div></div>
<div id="redes99" class="redes-articulo">
  <a href="https://www.facebook.com/sharer/sharer.php?u=x">fb</a>
</div>
<footer class="Footer">
  <a href="https://ifcncodeofprinciples.poynter.org/">IFCN badge</a>
</footer>
</body></html>"""

SYNTH_ARTICLE_DATOS_CLAVES = """<html><body>
<div class="row cuestionable text-articulos">
  <h2>Synthetic headline two</h2>
  <div class="col-12 col-md-9">
    <div id="datos-claves">
      <h2>2 DATOS CLAVE</h2>
      <ol><li>Invented key point with a
      <a href="https://should-not-appear.test/x">link that must be excluded</a>
      </li></ol>
    </div>
    <div>
      <p>The prose container carries much more invented text than the key-facts
      box, so longest-text selection must pick this div and not the box. It
      cites <a href="https://www.minsalud.gov.co/synthetic-page">MinSalud</a>
      in passing, plus enough filler words to stay clearly the longest child:
      lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
      tempor incididunt ut labore et dolore magna aliqua.</p>
    </div>
  </div>
</div>
</body></html>"""

SYNTH_LISTING = """<html><body>
<div class="listado">
  <a href="/chequeos/uno-inventado">card</a>
  <a href="/chequeos/dos-inventado">card</a>
</div>
<footer class="Footer">
  <a href="https://ifcncodeofprinciples.poynter.org/">IFCN badge</a>
</footer>
</body></html>"""


@pytest.fixture
def article_html() -> str:
    """Full synthetic article page (verdict `falso`, boilerplate outside)."""
    return SYNTH_ARTICLE


@pytest.fixture
def datos_claves_html() -> str:
    """Synthetic article whose column holds `#datos-claves` plus the prose."""
    return SYNTH_ARTICLE_DATOS_CLAVES


@pytest.fixture
def listing_html() -> str:
    """Synthetic listing page: no `text-articulos` wrapper at all."""
    return SYNTH_LISTING
