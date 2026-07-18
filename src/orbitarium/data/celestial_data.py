"""The body tree: which bodies exist and what orbits what.

CELESTIAL_DATA holds structure only (name, type, children). Numeric data
lives in the sibling modules, keyed by the names used here:

* physical properties (GM, mass, radius, with sources) -- ``physical.PHYSICAL``
* heliocentric orbital elements -- ``elements.PLANET_ELEMENTS``
* satellite orbital elements -- ``satellites.SATELLITE_ELEMENTS``

The nesting order below is part of the public contract: ``get_positions``
mirrors it, and the flat feature-vector API iterates it depth-first, so
reordering or removing entries is a breaking change. Planets are ordered
by distance from the Sun; moons by mean distance from their parent, with
co-orbital companions listed right after the body whose orbit they share
(trojans after their primary; Epimetheus after Janus as the horseshoe
pair's lighter member).
"""


def _body(name, kind, orbitals=()):
    return {"name": name, "type": kind, "orbitals": list(orbitals)}


CELESTIAL_DATA = {
    "sol": _body("sol", "star", [
        _body("mercury", "planet"),
        _body("venus", "planet"),
        _body("earth", "planet", [
            _body("luna", "moon"),
        ]),
        _body("mars", "planet", [
            _body("phobos", "moon"),
            _body("deimos", "moon"),
        ]),
        _body("jupiter", "planet", [
            _body("metis", "moon"),
            _body("adrastea", "moon"),
            _body("amalthea", "moon"),
            _body("thebe", "moon"),
            _body("io", "moon"),
            _body("europa", "moon"),
            _body("ganymede", "moon"),
            _body("callisto", "moon"),
        ]),
        _body("saturn", "planet", [
            _body("pan", "moon"),
            _body("daphnis", "moon"),
            _body("atlas", "moon"),
            _body("prometheus", "moon"),
            _body("pandora", "moon"),
            _body("janus", "moon"),
            _body("epimetheus", "moon"),
            _body("aegaeon", "moon"),
            _body("mimas", "moon"),
            _body("methone", "moon"),
            _body("anthe", "moon"),
            _body("pallene", "moon"),
            _body("enceladus", "moon"),
            _body("tethys", "moon"),
            _body("telesto", "moon"),
            _body("calypso", "moon"),
            _body("dione", "moon"),
            _body("helene", "moon"),
            _body("polydeuces", "moon"),
            _body("rhea", "moon"),
            _body("titan", "moon"),
            _body("hyperion", "moon"),
            _body("iapetus", "moon"),
            _body("phoebe", "moon"),
        ]),
        _body("uranus", "planet", [
            _body("cordelia", "moon"),
            _body("ophelia", "moon"),
            _body("bianca", "moon"),
            _body("cressida", "moon"),
            _body("desdemona", "moon"),
            _body("juliet", "moon"),
            _body("portia", "moon"),
            _body("rosalind", "moon"),
            _body("cupid", "moon"),
            _body("belinda", "moon"),
            _body("perdita", "moon"),
            _body("puck", "moon"),
            _body("mab", "moon"),
            _body("miranda", "moon"),
            _body("ariel", "moon"),
            _body("umbriel", "moon"),
            _body("titania", "moon"),
            _body("oberon", "moon"),
        ]),
        _body("neptune", "planet", [
            _body("naiad", "moon"),
            _body("thalassa", "moon"),
            _body("despina", "moon"),
            _body("galatea", "moon"),
            _body("larissa", "moon"),
            _body("hippocamp", "moon"),
            _body("proteus", "moon"),
            _body("triton", "moon"),
            _body("nereid", "moon"),
        ]),
        _body("pluto", "dwarf planet", [
            _body("charon", "moon"),
            _body("styx", "moon"),
            _body("nix", "moon"),
            _body("kerberos", "moon"),
            _body("hydra", "moon"),
        ]),
    ]),
}
