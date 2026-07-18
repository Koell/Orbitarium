"""Physical parameters for Solar System bodies, verbatim from JPL sources.

All values were retrieved on 2026-07-18 (2026-07-19 for the moons added
with the 67-moon catalog) from the following JPL sources:

* Sun GM:
    https://ssd.jpl.nasa.gov/astro_par.html
    "heliocentric gravitational constant GM_sun = 1.32712440041279419 x 10^20
    m^3 s^-2" (DE440), converted to km^3 s^-2 by dividing by 10^9.
* Sun radius:
    JPL Horizons object data for body 10 (https://ssd.jpl.nasa.gov/api/
    horizons.api?format=text&COMMAND='10'&OBJ_DATA='YES'&MAKE_EPHEM='NO'):
    "Vol. mean radius, km = 695700" / "Solar radius (IAU2015) = 695700 km"
    (the IAU 2015 nominal solar radius).
* Planet (and Pluto) GM:
    NAIF/JPL DE440 gravitational parameter kernel
    https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/gm_de440.tpc
    (BODY199_GM ... BODY999_GM; planet-only values, not planetary-system
    values). The JPL page https://ssd.jpl.nasa.gov/planets/phys_par.html
    publishes masses derived from these same GM estimates but does not list
    GM itself.
* Planet (and Pluto) mean radius:
    https://ssd.jpl.nasa.gov/planets/phys_par.html ("Mean Radius" column,
    with 1-sigma uncertainties).
* Satellite GM and mean radius:
    https://ssd.jpl.nasa.gov/sats/phys_par/ (main table; GM reference
    solutions DE440, MAR097, JUP365, SAT441, URA111, NEP097/NEP101, PLU060,
    with 1-sigma uncertainties).
* Kerberos GM (blank in the sats/phys_par table):
    BODY904_GM from the NAIF/JPL kernel gm_de440.tpc (gm_Horizons.pck value).
* Telesto and Calypso GM (absent from the sats/phys_par table):
    the JPL Horizons object data pages for bodies 613/614
    ("GM (km^3/s^2) = 0.00048" / "= 0.00024").
* Small-moon radii absent from the sats/phys_par table:
    - Puck and the Uranian inner belt (Cordelia through Belinda): the JPL
      Horizons object data pages for bodies 706-715 ("Radius (km) = NN
      +- N").
    - Telesto, Calypso, Daphnis, Methone, Pallene, Polydeuces, Anthe,
      Aegaeon: triaxial BODYnnn_RADII from the NAIF/JPL kernel
      pck00011.tpc; the tabulated value is the DERIVED volumetric mean
      radius (a*b*c)^(1/3), matching the "radius of a sphere with the
      equivalent volume" definition used by sats/phys_par.
    - Perdita, Mab, Cupid: no JPL-published radius exists (Horizons lists
      no physical data); mean radii from the discovery/characterization
      paper Showalter & Lissauer 2006 (Science 311, 973). Mab's radius
      assumes a Puck-like albedo (stated in the paper).
    - Hippocamp: no JPL-published radius exists; mean radius from
      Showalter et al. 2019 (Nature 566, 350).

Missing data (fields set to None):

* nereid: JPL's sats/phys_par table lists Nereid's GM as 0.00000 (NEP101),
  i.e. not determined; no other JPL-published GM was found, so gm_km3_s2
  and mass_kg are None.
* styx: JPL's sats/phys_par table leaves Styx's GM blank (PLU060) and
  gm_de440.tpc carries BODY905_GM = 0.0, so gm_km3_s2 and mass_kg are None.
* daphnis, methone, pallene, polydeuces, anthe, aegaeon, puck, cordelia,
  ophelia, bianca, cressida, desdemona, juliet, portia, rosalind, belinda,
  perdita, mab, cupid, hippocamp: JPL publishes no GM for these small
  moons (absent from sats/phys_par, blank in Horizons object data, absent
  from gm_de440.tpc), so gm_km3_s2 and mass_kg are None. Their orbits do
  not need it: satellite states derive the parent's effective GM from the
  fitted mean motion (see data.satellites).

Derivation note:
    JPL's primary measured quantity is GM (the gravitational parameter),
    not mass. The ``mass_kg`` values below are therefore DERIVED as
    mass_kg = GM / G using the CODATA 2018 constant
    G = 6.67430e-11 m^3 kg^-1 s^-2 = 6.67430e-20 km^3 kg^-1 s^-2.
    GM and radius digits are verbatim from the sources above.

Each ``PHYSICAL`` entry has the keys:
    gm_km3_s2         GM in km^3 s^-2 (float, or None -- see above)
    gm_sigma_km3_s2   1-sigma uncertainty of GM, where published (or None)
    radius_km         mean radius in km (float)
    radius_sigma_km   1-sigma uncertainty of the radius, where published
    mass_kg           GM / G (float, or None when GM is None)
    source            provenance string
    retrieved         ISO date the values were read from the JPL sources
"""

# CODATA 2018: G = 6.67430e-11 m^3 kg^-1 s^-2, converted to km^3 kg^-1 s^-2.
G_KM3_KG_S2 = 6.67430e-20

_ASTRO_PAR = "JPL SSD astro_par.html (DE440 GM_Sun)"
_HORIZONS_SUN = "JPL Horizons body 10 (IAU 2015 nominal solar radius)"
_GM_DE440 = "NAIF/JPL gm_de440.tpc (DE440)"
_GM_HORIZONS = "NAIF/JPL gm_de440.tpc (gm_Horizons.pck value)"
_PLANETS_PAGE = "JPL SSD planets/phys_par.html (mean radius)"
_SATS_PAGE = "JPL SSD sats/phys_par"
_HORIZONS_OBJ = "JPL Horizons object data page"
_PCK11 = ("NAIF/JPL pck00011.tpc RADII; volumetric mean radius"
          " (a*b*c)^(1/3) derived")
_SL2006 = "Showalter & Lissauer 2006, Science 311, 973 (no JPL value)"
_SHOWALTER2019 = "Showalter et al. 2019, Nature 566, 350 (no JPL value)"

# name: (gm_km3_s2, gm_sigma, radius_km, radius_sigma, source)
_RAW = {
    "sol": (1.32712440041279419e11, None, 695700.0, None,
            _ASTRO_PAR + "; radius: " + _HORIZONS_SUN),
    # Planets and Pluto: GM from gm_de440.tpc (planet-only BODYn99 values),
    # mean radius from planets/phys_par.html.
    "mercury": (2.2031868551400003e+04, None, 2439.4, 0.1,
                _GM_DE440 + "; radius: " + _PLANETS_PAGE),
    "venus": (3.2485859200000000e+05, None, 6051.8, 1.0,
              _GM_DE440 + "; radius: " + _PLANETS_PAGE),
    "earth": (3.9860043550702266e+05, None, 6371.0084, 0.0001,
              _GM_DE440 + "; radius: " + _PLANETS_PAGE),
    "mars": (4.282837362069909e+04, None, 3389.50, 0.2,
             _GM_DE440 + "; radius: " + _PLANETS_PAGE),
    "jupiter": (1.266865319003704e+08, None, 69911.0, 6.0,
                _GM_DE440 + "; radius: " + _PLANETS_PAGE),
    "saturn": (3.793120623436167e+07, None, 58232.0, 6.0,
               _GM_DE440 + "; radius: " + _PLANETS_PAGE),
    "uranus": (5.793951256527211e+06, None, 25362.0, 7.0,
               _GM_DE440 + "; radius: " + _PLANETS_PAGE),
    "neptune": (6.835103145462294e+06, None, 24622.0, 19.0,
                _GM_DE440 + "; radius: " + _PLANETS_PAGE),
    "pluto": (8.696138177608748e+02, None, 1188.3, 1.6,
              _GM_DE440 + "; radius: " + _PLANETS_PAGE),
    # Satellites: GM and mean radius from sats/phys_par (solution in
    # parentheses). Listed as "Moon" on the JPL page; keyed "luna" here.
    "luna": (4902.800, 0.001, 1737.4, 0.1, _SATS_PAGE + " (DE440)"),
    "phobos": (0.0007087, 0.0000006, 11.08, 0.04, _SATS_PAGE + " (MAR097)"),
    "deimos": (0.0000962, 0.0000028, 6.2, 0.24, _SATS_PAGE + " (MAR097)"),
    "io": (5959.91547, 0.00135, 1821.49, 0.50, _SATS_PAGE + " (JUP365)"),
    "europa": (3202.71210, 0.00181, 1560.80, 0.30, _SATS_PAGE + " (JUP365)"),
    "ganymede": (9887.83275, 0.00247, 2631.20, 1.70,
                 _SATS_PAGE + " (JUP365)"),
    "callisto": (7179.28340, 0.00324, 2410.30, 1.50,
                 _SATS_PAGE + " (JUP365)"),
    "amalthea": (0.16456, 0.00867, 83.50, 3.00, _SATS_PAGE + " (JUP365)"),
    "thebe": (0.03015, 0.01250, 49.30, 4.00, _SATS_PAGE + " (JUP365)"),
    "adrastea": (0.00014, 0.00020, 8.20, 4.00, _SATS_PAGE + " (JUP365)"),
    "metis": (0.00250, 0.00160, 21.50, 4.00, _SATS_PAGE + " (JUP365)"),
    "mimas": (2.50349, 0.00014, 198.20, 0.40, _SATS_PAGE + " (SAT441)"),
    "enceladus": (7.21037, 0.00009, 252.10, 0.20, _SATS_PAGE + " (SAT441)"),
    "tethys": (41.21353, 0.00031, 531.10, 0.60, _SATS_PAGE + " (SAT441)"),
    "dione": (73.11607, 0.00005, 561.40, 0.40, _SATS_PAGE + " (SAT441)"),
    "rhea": (153.94175, 0.00041, 763.50, 0.60, _SATS_PAGE + " (SAT441)"),
    "titan": (8978.13710, 0.00025, 2574.76, 0.02, _SATS_PAGE + " (SAT441)"),
    "hyperion": (0.37049, 0.00005, 135.00, 4.00, _SATS_PAGE + " (SAT441)"),
    "iapetus": (120.51511, 0.00242, 734.30, 2.80, _SATS_PAGE + " (SAT441)"),
    "phoebe": (0.55479, 0.00108, 106.50, 0.70, _SATS_PAGE + " (SAT441)"),
    "janus": (0.12662, 0.00007, 89.2, 0.8, _SATS_PAGE + " (SAT415)"),
    "epimetheus": (0.03514, 0.00002, 58.2, 1.2, _SATS_PAGE + " (SAT415)"),
    "helene": (0.00048, 0.00002, 18.00, 0.40, _SATS_PAGE + " (SAT441)"),
    "atlas": (0.00037, 0.00001, 15.1, 0.8, _SATS_PAGE + " (SAT415)"),
    "prometheus": (0.01071, 0.00001, 43.1, 1.2, _SATS_PAGE + " (SAT415)"),
    "pandora": (0.00926, 0.00002, 40.6, 1.5, _SATS_PAGE + " (SAT415)"),
    "pan": (0.00028, 0.00014, 14.0, 1.2, _SATS_PAGE + " (SAT415)"),
    # Telesto/Calypso: GM only on their Horizons object data pages;
    # radius derived from pck00011 triaxial RADII (see module docstring).
    "telesto": (0.00048, None, 12.353, None,
                _HORIZONS_OBJ + " (613); radius: " + _PCK11),
    "calypso": (0.00024, None, 9.642, None,
                _HORIZONS_OBJ + " (614); radius: " + _PCK11),
    # Small Saturnian moons without any JPL-published GM (see docstring).
    "daphnis": (None, None, 3.870, None, _PCK11),
    "methone": (None, None, 1.447, None, _PCK11),
    "pallene": (None, None, 2.209, None, _PCK11),
    "polydeuces": (None, None, 1.216, None, _PCK11),
    "anthe": (None, None, 0.5, None, _PCK11),
    "aegaeon": (None, None, 0.327, None, _PCK11),
    "ariel": (83.5, 1.4, 578.9, 0.6, _SATS_PAGE + " (URA111)"),
    "umbriel": (85.1, 1.9, 584.7, 2.8, _SATS_PAGE + " (URA111)"),
    "titania": (226.9, 4.1, 788.9, 1.8, _SATS_PAGE + " (URA111)"),
    "oberon": (205.3, 5.8, 761.4, 2.6, _SATS_PAGE + " (URA111)"),
    "miranda": (4.3, 0.2, 235.8, 0.7, _SATS_PAGE + " (URA111)"),
    # Puck and the Uranian inner belt: no JPL-published GM; radii from
    # their Horizons object data pages ("Radius (km) = NN +- N").
    "puck": (None, None, 77.0, 3.0, _HORIZONS_OBJ + " (715)"),
    "cordelia": (None, None, 13.0, 2.0, _HORIZONS_OBJ + " (706)"),
    "ophelia": (None, None, 16.0, 2.0, _HORIZONS_OBJ + " (707)"),
    "bianca": (None, None, 22.0, 3.0, _HORIZONS_OBJ + " (708)"),
    "cressida": (None, None, 33.0, 4.0, _HORIZONS_OBJ + " (709)"),
    "desdemona": (None, None, 29.0, 3.0, _HORIZONS_OBJ + " (710)"),
    "juliet": (None, None, 42.0, 5.0, _HORIZONS_OBJ + " (711)"),
    "portia": (None, None, 55.0, 6.0, _HORIZONS_OBJ + " (712)"),
    "rosalind": (None, None, 29.0, 4.0, _HORIZONS_OBJ + " (713)"),
    "belinda": (None, None, 34.0, 4.0, _HORIZONS_OBJ + " (714)"),
    # Perdita/Mab/Cupid: no JPL-published physical data at all; radii
    # from the HST discovery paper (Mab assumes a Puck-like albedo).
    "perdita": (None, None, 13.3, 0.7, _SL2006),
    "mab": (None, None, 12.4, 0.5, _SL2006 + "; Puck-like albedo assumed"),
    "cupid": (None, None, 8.9, 0.7, _SL2006),
    "triton": (1428.49546, 0.61603, 1352.60, 2.40,
               _SATS_PAGE + " (NEP097)"),
    "naiad": (0.00853, 0.00480, 29.00, 6.00, _SATS_PAGE + " (NEP097)"),
    "thalassa": (0.02359, 0.00522, 40.00, 8.00, _SATS_PAGE + " (NEP097)"),
    "despina": (0.11673, 0.25263, 74.00, 10.00, _SATS_PAGE + " (NEP097)"),
    "galatea": (0.18990, 0.76278, 79.00, 12.00, _SATS_PAGE + " (NEP097)"),
    "larissa": (0.25484, 3.12230, 96.00, 7.00, _SATS_PAGE + " (NEP097)"),
    # Hippocamp: no JPL-published physical data; radius from the
    # characterization paper.
    "hippocamp": (None, None, 17.4, 2.0, _SHOWALTER2019),
    # Nereid: GM listed as 0.00000 (undetermined) on sats/phys_par; None.
    "nereid": (None, None, 170.00, 25.00,
               _SATS_PAGE + " (NEP101; GM not determined by JPL)"),
    "proteus": (2.58342, 2.42070, 208.00, 8.00, _SATS_PAGE + " (NEP097)"),
    "charon": (106.1, 0.3, 606.0, 0.5, _SATS_PAGE + " (PLU060)"),
    "nix": (0.0015, 0.0005, 18.0, 1.0, _SATS_PAGE + " (PLU060)"),
    "hydra": (0.0020, 0.0003, 18.5, 1.0, _SATS_PAGE + " (PLU060)"),
    # Kerberos: GM blank on sats/phys_par; BODY904_GM from gm_de440.tpc.
    "kerberos": (1.110040850536676e-03, None, 6.0, 1.0,
                 _SATS_PAGE + " (PLU060 radius); GM: " + _GM_HORIZONS),
    # Styx: GM blank on sats/phys_par and 0.0 in gm_de440.tpc; None.
    "styx": (None, None, 5.2, 1.0,
             _SATS_PAGE + " (PLU060; GM not determined by JPL)"),
}

_RETRIEVED = "2026-07-18"
# Moons added with the 67-moon catalog were retrieved a day later.
_RETRIEVED_67 = "2026-07-19"
_ADDED_WITH_67_MOON_CATALOG = frozenset({
    "thebe", "adrastea", "metis",
    "tethys", "dione", "hyperion", "phoebe", "janus", "epimetheus",
    "helene", "atlas", "prometheus", "pandora", "pan", "telesto",
    "calypso", "daphnis", "methone", "pallene", "polydeuces", "anthe",
    "aegaeon",
    "puck", "cordelia", "ophelia", "bianca", "cressida", "desdemona",
    "juliet", "portia", "rosalind", "belinda", "perdita", "mab", "cupid",
    "naiad", "thalassa", "despina", "galatea", "larissa", "hippocamp",
})

PHYSICAL = {
    name: {
        "gm_km3_s2": gm,
        "gm_sigma_km3_s2": gm_sigma,
        "radius_km": radius,
        "radius_sigma_km": radius_sigma,
        # Mass is DERIVED from JPL's GM using CODATA G (see module docstring).
        "mass_kg": None if gm is None else gm / G_KM3_KG_S2,
        "source": source,
        "retrieved": (
            _RETRIEVED_67 if name in _ADDED_WITH_67_MOON_CATALOG
            else _RETRIEVED
        ),
    }
    for name, (gm, gm_sigma, radius, radius_sigma, source) in _RAW.items()
}
