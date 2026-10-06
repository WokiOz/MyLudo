"""Réponses BoardGameGeek simulées : aucun appel réseau dans les tests."""

import httpx

SEARCH = """<?xml version="1.0"?>
<items total="3">
  <item type="boardgameexpansion" id="200"><name type="primary" value="Catan : Marins"/><yearpublished value="1997"/></item>
  <item type="boardgame" id="13"><name type="primary" value="Catan"/><yearpublished value="1995"/></item>
  <item type="boardgame" id="14"><name type="primary" value="Catan Junior"/></item>
</items>"""

CATAN = """<?xml version="1.0"?>
<items><item type="boardgame" id="13">
  <image>https://img.example/catan.jpg</image>
  <name type="alternate" value="Les Colons de Catane"/>
  <name type="primary" value="Catan"/>
  <yearpublished value="1995"/>
  <minplayers value="3"/><maxplayers value="4"/>
  <poll name="suggested_numplayers" title="Nombre de joueurs">
    <results numplayers="3"><result value="Best" numvotes="900"/><result value="Recommended" numvotes="300"/><result value="Not Recommended" numvotes="20"/></results>
    <results numplayers="4"><result value="Best" numvotes="800"/><result value="Recommended" numvotes="400"/><result value="Not Recommended" numvotes="30"/></results>
    <results numplayers="5"><result value="Best" numvotes="100"/><result value="Recommended" numvotes="500"/><result value="Not Recommended" numvotes="200"/></results>
    <results numplayers="5+"><result value="Best" numvotes="1"/><result value="Recommended" numvotes="1"/><result value="Not Recommended" numvotes="1"/></results>
  </poll>
  <playingtime value="120"/><minplaytime value="60"/><maxplaytime value="120"/>
  <minage value="10"/>
  <link type="boardgamecategory" id="1" value="Negotiation"/>
  <link type="boardgamecategory" id="2" value="Inconnue de la table"/>
  <link type="boardgamemechanic" id="3" value="Trading"/>
  <link type="boardgamemechanic" id="4" value="Dice Rolling"/>
  <link type="boardgamemechanic" id="5" value="Worker Placement"/>
  <link type="boardgamepublisher" id="6" value="Kosmos"/>
  <link type="boardgamepublisher" id="7" value="Filosofia"/>
  <statistics page="1"><ratings><average value="7.1234"/><averageweight value="2.32"/></ratings></statistics>
</item></items>"""

MARINS = """<?xml version="1.0"?>
<items><item type="boardgameexpansion" id="200">
  <name type="primary" value="Catan : Marins"/>
  <yearpublished value="1997"/>
  <minplayers value="3"/><maxplayers value="4"/>
  <minplaytime value="60"/><maxplaytime value="120"/>
  <link type="boardgameexpansion" id="13" value="Catan" inbound="true"/>
</item></items>"""

EMPTY = '<?xml version="1.0"?><items></items>'
PAGES = {"13": CATAN, "200": MARINS}


def bgg_transport(status: int = 200, queued: int = 0) -> httpx.MockTransport:
    """`queued` : nombre de réponses 202 (en préparation) avant la vraie réponse."""
    state = {"queued": queued}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer jeton"
        if status != 200:
            return httpx.Response(status)
        if state["queued"] > 0:
            state["queued"] -= 1
            return httpx.Response(202)
        if request.url.path.endswith("/search"):
            return httpx.Response(200, text=SEARCH)
        return httpx.Response(200, text=PAGES.get(request.url.params["id"], EMPTY))

    return httpx.MockTransport(handler)
