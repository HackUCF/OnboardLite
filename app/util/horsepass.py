# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import random

# not as much HorsePass anymore.
wordlist = [
    "Thoroughbred",
    "Arabian",
    "QuarterHorse",
    "PaintHorse",
    "Appaloosa",
    "Walking",
    "Standardbred",
    "Andalusian",
    "Percheron",
    "Morgan",
    "Friesian",
    "PasoFino",
    "Welsh",
    "Shetland",
    "Clydesdale",
    "Palomino",
    "Haflinger",
    "Mustang",
    "AkhalTeke",
    "GypsyVanner",
    "Pegasus",
    "Lusitano",
    "Connemara",
    "Trakehner",
    "Hanoverian",
    "Oldenburg",
    "SelleFrancais",
    "Holsteiner",
    "IrishSport",
    "Lipizzan",
    "Freiberger",
    "Knabstrupper",
    "RockyMountain",
    "TennesseeWalking",
    "AmericanSaddlebred",
    "Icelandic",
    "Peruvian",
    "Canadian",
    "DutchWarmblood",
    "Fjord",
    "NorwegianFjord",
    "BelgianWarmblood",
    "SwedishWarmblood",
    "DanishWarmblood",
    "GermanWarmblood",
    "AustralianStock",
    "Criollo",
    "SuffolkPunch",
    "NewForest",
    "WelshCob",
    "Hackney",
    "Highland",
    "ThuringianWarmblood",
    "Westphalian",
    "Fell",
    "Galician",
    "ArabianCross",
    "Trotter",
    "Gelderlander",
    "OrlovTrotter",
    "Pintabian",
    "Morab",
    "Warlander",
    "IrishCob",
    "Dartmoor",
    "Exmoor",
    "BashkirCurly",
    "BlackForest",
    "Brandenburger",
    "HaflingerCross",
    "IrishDraught",
    "Jutland",
    "Karabakh",
    "LipizzanCross",
    "Mecklenburger",
    "Miniature",
    "Mule",
    "MustangCross",
    "NormanCob",
    "Pleven",
    "Sanhe",
    "SchleswigerHeavyDraft",
    "Schwarzwald",
    "Senner",
    "SpanishJennet",
    "Taishuh",
    "Tawleed",
    "Tchernomor",
    "Waler",
    "Wielkopolski",
    "Knugget",
    "Mare",
    "Stallion",
    "Filly",
    "Foal",
    "Colt",
    "Pony",
    "Plinko",
    "Horse",
    "Helsinki",
    "Lexington",
    "BuenosAires",
    "Dubai",
    "Paris",
    "Tokyo",
    "Orlando",
    "Aachen",
    "Sydney",
    "Nitro",
    "Cyber",
    "Challenger",
    "Equestrian",
    "Gallop",
    "Steed",
    "Lance",
    "Armor",
    "Encryption",
    "Castle",
    "Firewall",
    "Cavalry",
    "Hacking",
    "Sword",
    "Trojan",
    "Jousting",
    "Code",
    "Shield",
    "Digital",
    "Equine",
    "Hacktivist",
    "Chivalry",
    "Malware",
    "Lancer",
    "Algorithm",
    "Knightly",
    "Secure",
    "Pentesting",
    "Courage",
    "Bug",
    "Labyrinth",
    "VPN",
    "Loyal",
    "Phishing",
    "Quest",
    "Keylogger",
    "Excalibur",
    "Defender",
    "Spear",
    "Noble",
    "Virus",
    "Questing",
    "Cryptography",
    "Charger",
    "Incognito",
    "Dragon",
    "Vigilant",
    "Ransomware",
    "Brave",
    "Circuit",
    "Damsel",
    "Vulnerability",
    "Fortress",
    "Hacker",
    "Heroic",
    "Decryption",
    "Sir",
    "Security",
    "Fireswall",
    "Epic",
    "Sentinel",
    "Data",
    "Chivalrous",
    "Resilient",
    "Horsepower",
    "Swordplay",
    "Intrusion",
    "Majestic",
    "Cybersecurity",
    "Guardian",
    "Paladin",
    "Cyberspace",
    "Valiant",
    "Hack",
    "Champion",
    "Key",
    "Joust",
    "Knight",
    "UCF",
    "Astronomy",
    "Astronaut",
    "Spaceship",
    "Star",
    "Galaxy",
    "Cosmos",
    "BlackHole",
    "Nebula",
    "Comet",
    "Meteor",
    "Planet",
    "Satellite",
    "Orbit",
    "Constellation",
    "Eclipse",
    "Interstellar",
    "SolarSystem",
    "Telescope",
    "Exoplanet",
    "Asteroid",
    "Celestial",
    "Gravity",
    "Spacewalk",
    "Spacecraft",
    "Martian",
    "Lunar",
    "Extraterrestrial",
    "Rocket",
    "Alien",
    "UFO",
    "Cosmonaut",
    "Astrophysics",
    "Hubble",
    "AstroidBelt",
    "SpaceStation",
    "Stellar",
    "Microgravity",
    "Supernova",
    "Cosmic",
    "Telemetry",
    "Soyuz",
    "Cosmodrome",
    "Liftoff",
    "SpaceTime",
    "Telemetry",
    "Spacesuit",
    "SpaceProbe",
    "Astronomer",
    "Planetarium",
    "Orbital",
    "Voyager",
    "Landing",
    "OuterSpace",
    "Infrared",
    "Spectroscopy",
    "Astrobiology",
    "RedDwarf",
    "WhiteDwarf",
    "Galactic",
    "SpaceAgency",
    "Observatory",
    "DarkMatter",
    "CosmicRays",
    "StarCluster",
    "SpaceRace",
    "AstronomicalUnit",
    "MilkyWay",
    "EventHorizon",
    "GravityWave",
    "SpaceX",
    "SpaceWalk",
    "CelestialBody",
    "LaunchPad",
    "LunarModule",
    "SpaceShuttle",
    "RocketScience",
    "SaturnV",
    "CosmicBackground",
    "SpaceDebris",
    "CosmicDust",
    "HubbleSpace",
    "AstronomicalObservation",
    "StarDust",
    "SolarFlare",
    "Interplanetary",
    "Solarsail",
    "Astrolabe",
    "Astrochemistry",
    "Planetoid",
    "AstronomicalPhenomenon",
    "OrbitalMechanics",
    "MicrogravityResearch",
    "SpacePolicy",
    "OuterPlanets",
    "SpaceCommunications",
    "Astrogeology",
    "StellarNucleosynthesis",
    "SpaceHabitat",
    "SpacePioneer",
    "StellarEvolution",
    "ExoplanetaryResearch",
    "SpaceTourism",
    "SpaceResearch",
    "Astroengineering",
    "CosmicJourney",
    "SpaceExploration",
    "SpaceTimeContinuum",
    "ZeroGravity",
    "SpaceCruise",
    "StellarSpectrum",
    "CometTail",
    "SpaceInnovation",
    "CelestialNavigation",
    "GalacticCenter",
    "SolarObservatory",
    "NebulaeClusters",
    "StarFormation",
    "GravityAssist",
    "LunarCrater",
    "Astrophotography",
    "SpaceElevator",
    "CelestialMechanics",
    "OrbitalDynamics",
    "Astroinformatics",
    "SupernovaRemnant",
    "StellarWinds",
    "LunarRover",
    "SpaceWeather",
    "OrbitalDecay",
    "CosmicMicrowaveBackground",
    "Planetesimal",
    "SpaceAnomaly",
    "CelestialHorizon",
    "GravityField",
    "LunarLanding",
    "AstrophysicalProcesses",
    "StellarFusion",
    "SolarProminence",
    "OrbitalInsertion",
    "Astroclimatology",
    "CosmicScale",
    "StellarParallax",
    "OrbitalVelocity",
    "Astrotheology",
    "StarCatalogue",
    "CelestialSphere",
    "GalacticRotation",
    "SolarPhysics",
    "ExoplanetObservation",
    "CosmicChemistry",
    "SpaceTether",
    "PlanetaryRing",
    "Astrochronology",
    "StellarNursery",
    "OrbitalPeriod",
    "AstronomicalDistance",
    "StellarMagnitude",
    "SpaceLaws",
    "CelestialEquator",
    "OrbitalManeuver",
    "Astrodiversity",
    "StellarPopulation",
    "CosmicTimeline",
    "OrbitalDebris",
    "SpaceArcheology",
    "CelestialEvent",
    "Spaceport",
    "SpaceXplorer",
    "StellarRadiation",
    "Astroethics",
    "SolarWind",
    "OrbitalResonance",
    "CelestialBodies",
    "OrbitalPerturbation",
    "Astrobiology",
    "StellarSpectroscopy",
    "CosmicOrigin",
    "PlanetaryNebula",
    "Astrography",
    "SolarObservation",
    "OrbitalRendezvous",
    "CelestialBiology",
    "LunarEclipse",
    "StellarStructure",
    "Astrocartography",
    "CosmicHorizon",
    "CelestialTime",
    "SpaceGreenhouse",
    "LunarBase",
    "StellarCluster",
    "Astrophysicist",
    "Planetesimal",
    "StellarDynamics",
    "OrbitalSatellite",
    "SpaceTreaty",
    "CelestialHarmony",
    "GalacticRedshift",
    "Astroarchaeology",
    "StellarCartography",
    "OrbitalMotion",
    "CosmicTravel",
    "Astroambience",
    "LunarColony",
    "StellarFission",
    "SpaceLaw",
    "CelestialHarmony",
    "GalacticRedshift",
    "Astroarchaeology",
    "StellarCartography",
    "OrbitalMotion",
    "CosmicTravel",
    "Astroambience",
    "LunarColony",
    "StellarFission",
    "SpaceLaw",
]


class HorsePass:
    """
    The Horse Plinko password generator
    """

    def __init__(self):
        pass

    def gen():
        word1, word2, word3, word4 = random.sample(wordlist, 4)
        password = f"{word1}-{word2}-{word3}-{word4}-{random.randint(0, 99):02}"
        return password
