#!/usr/bin/env python3

import datetime
import requests
from hashlib import md5
import sys
import argparse
import webbrowser

# Websites that return the Dow Jones index in plain text
# The date can be appended to the URL in this format: %Y/%m/%d
DOW_JONES_SOURCES = ["https://data.geohashing.info/dow/", "http://geo.crox.net/djia/",
                     "http://www1.geo.crox.net/djia/", "http://www2.geo.crox.net/djia/",
                     "http://carabiner.peeron.com/xkcd/map/data/",
                     ]


def get_dow_jones(east=False, date=None):
    """
    The date will be derived from the computer clock, but if it is manually supplied,
    it must be in a datetime.date object.

    Set `east` to true if your current location is East of -30 longitude.
    """
    if date is None:
        date = datetime.date.today()
    if east:  # Subtract a day to make this 30W compliant
        date += datetime.timedelta(days=-1)

    date = date.strftime("%Y/%m/%d")
    for url in DOW_JONES_SOURCES:
        try:
            r = requests.get(url + date, timeout=5)
        except requests.exceptions.ReadTimeout:
            continue  # Try another source, this one is offline
        # Otherwise, check and return the result found
        if r.status_code == 200:
            return r.text.strip()

    # All URLs have been tried and failed
    raise Exception("None of the programmed Dow Jones sources are online, or no data exists for your date yet.\nTry providing one manually.")


def get_hash(east=False, date=None, dow_jones=None, is_simple=False):
    """Get the md5 hash.

    dow_jones can be a string or number. If it is None, then the current value
    will be used.
    `date` will be derived from the computer clock, but if it is manually supplied,
    it must be in a datetime.date object.

    The hash will be returned as a hexadecimal string.
    """

    if date is None:
        date = datetime.date.today()
    if dow_jones is None:
        dow_jones = get_dow_jones(east, date)
    # Reformat
    dow_jones = str(dow_jones)
    date = date.strftime("%Y-%m-%d")
    if is_simple is False:
        print(f"DOW Jones Index on provided date {date}: {dow_jones}")

    return md5(date.encode() + b"-" + dow_jones.encode()).hexdigest()


def hash_to_location(u_lat, u_lon, md5_hash):
    """Returns (lat, lon) as floats."""

    h1 = md5_hash[:16]
    h2 = md5_hash[16:]
    # Append the base10 conversion as decimals
    lat = str(int(u_lat)) + str(float.fromhex("0." + h1))[1:]
    lon = str(int(u_lon)) + str(float.fromhex("0." + h2))[1:]
    return float(lat), float(lon)


def geohash(lat, lon, date=None, dow_jones=None, east=None, is_simple=False):
    """Get an xkcd geohash for the supplied position.

    This function is 30W compliant. If `east` is specified than this functionality
    is overrided.
    """

    if east is None:
        east = False
        if lon > -30:
            east = True

    return hash_to_location(lat, lon, get_hash(east, date, dow_jones, is_simple))


def globalhash(date=None, dow_jones=None, is_simple=False):
    lat, lon = geohash(0, 0, date, dow_jones, east=True, is_simple=is_simple)
    lat = lat * 180 - 90
    lon = lon * 360 - 180
    return lat, lon


def replace_tenths(dst, src):
    """Replace tenths place in dst with that from src"""

    new_tenths = int(abs(src) * 10) % 10
    old_tenths = int(abs(dst) * 10) % 10
    dst = str(dst)
    return float(dst.replace(f'.{old_tenths}', f'.{new_tenths}'))


def check_find_nearby(lat, lon, args):
    if args["near_lat_start"] or args["near_lat_stop"] or args["near_lon_start"] or args["near_lon_stop"]:
        if args["near_lat_start"] is None:
            args["near_lat_start"] = 0
        else:
            if not -90 <= lat - args["near_lat_start"] <= 90:
                raise ValueError(f"Latitude graticule {lat} must lie between (-90, 90), "
                                 f"but provided value 'near_lat_start' gives a start latitude of {lat - args['near_lat_start']}.")
        if args["near_lat_stop"] is None:
            args["near_lat_stop"] = 0
        else:
            if not -90 <= lat + args["near_lat_stop"] <= 90:
                raise ValueError(f"Latitude graticule {lat} must lie between (-90, 90), "
                                 f"but provided value 'near_lat_stop' gives an end latitude of {lat + args['near_lat_stop']}.")

        if args["near_lat_start"] > args["near_lat_stop"]:
            raise ValueError("Latitude start cannot be greater than stop.")

        if args["near_lon_start"] is None:
            args["near_lon_start"] = 0
        else:
            if not -180 <= lon - args["near_lon_start"] <= 180:
                raise ValueError(f"Longitude graticule {lon} must lie between (-180, 180), "
                                 f"but provided value 'near_lon_stop' gives a start longitude of {lon - args['near_lon_start']}.")
        if args["near_lon_stop"] is None:
            args["near_lon_stop"] = 0
        else:
            if not -180 <= lon + args["near_lon_stop"] <= 180:
                raise ValueError(f"Longitude graticule {lon} must lie between (-180, 180), "
                                 f"but provided value 'near_lon_stop' gives an end longitude of {lon + args['near_lon_stop']}.")

        if args["near_lon_start"] > args["near_lon_stop"]:
            raise ValueError("Longitude start cannot be greater than stop.")

        print("Graticules nearby:")
        for lat_offset in range(args["near_lat_start"], args["near_lat_stop"] + 1):
            for lon_offset in range(args["near_lon_start"], args["near_lon_stop"] + 1):
                if lat_offset == 0 and lon_offset == 0:
                    continue
                print_fancy_output(lat + lat_offset, lon + lon_offset, args["browser"])


def print_fancy_output(lat, lon, open_in_browser=None):
    print(f"Latitude:  {'' if lat < 0 else ' '}{lat}")  # Pad negative sign to be in line with longitude
    print(f"Longitude: {'' if lon < 0 else ' '}{lon}\n")

    gmap_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    osm_url = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=10"

    print(f"Google Maps:\n\t{gmap_url}\nOpenStreetMap:\n\t{osm_url}\n")
    if open_in_browser is not None:
        webbrowser.open(gmap_url if open_in_browser == 'g' else osm_url)


parser = argparse.ArgumentParser(description="Calculate geohashes as defined by Randall Munroe in xkcd #426.")
parser.add_argument("latitude", type=float, nargs='?', default=None, help="The latitude of your location (just the integer part is enough for graticule).")
parser.add_argument("longitude", type=float, nargs='?', default=None, help="The longitude of your location (just the integer part is enough for graticule).")
parser.add_argument("-d", "--date", help="The geohash date in YYYY-MM-DD format. The current date is used otherwise.")
parser.add_argument("-j", "--dow-jones", "--dj", type=float, help="The Dow Jones value, with two decimal places. The most recent compilant open value is used otherwise")
parser.add_argument("--30w", choices=("e", "w", "east", "west"), help="Override automatic 30W detection, forcing either east or west.")
parser.add_argument("-g", "--global", action="store_true", help="Calculate the globalhash instead. Lat and lon are ignored.")
parser.add_argument("-s", "--simple", action="store_true", help="Only return lat and lon, separated by a newline.")
parser.add_argument("--centicule", action="store_true", help="Calculate the centicule instead.")
parser.add_argument("-b", "--browser", choices=("g", "o"), default=None, help="Open in web browser. 'g' for Google Maps or 'o' for OpenStreetMaps.")
parser.add_argument("--near-lat-start", type=int, help="Calculate the graticules starting from x graticules away from input latitude.")
parser.add_argument("--near-lat-stop", type=int, help="Calculate the graticules ending at x graticules away from input latitude.")
parser.add_argument("--near-lon-start", type=int, help="Calculate the graticules starting from x graticules away from input longitude.")
parser.add_argument("--near-lon-stop", type=int, help="Calculate the graticules ending at x graticules away from input longitude.")
parser.add_argument("--open-og-comic", action="store_true", help="Open XKCD #426 in web browser.")
parser.add_argument("--open-geohashing-home", action="store_true", help="Open the homepage of Geohashing in web browser.")
args = vars(parser.parse_args())

# Checks
if not args["date"] is None:
    try:
        args["date"] = datetime.datetime.strptime(args["date"], "%Y-%m-%d").date()
    except ValueError:
        print("The date provided was not in YYYY-MM-DD format.")
        sys.exit(1)
if args["30w"] in ["e", "east"]:
    args["30w"] = True
elif args["30w"] in ["w", "west"]:
    args["30w"] = False

if args["global"]:
    lat, lon = globalhash(args["date"], args["dow_jones"], args["simple"])
else:
    if args["latitude"] is None or args["longitude"] is None:
        print("Latitude and longitude must be provided when not calculating the globalhash.")
        sys.exit(1)
    lat, lon = geohash(args["latitude"], args["longitude"], args["date"], args["dow_jones"], args["30w"], args["simple"])

if args["centicule"]:
    # See https://geohashing.site/geohashing/Centicule
    lat = replace_tenths(lat, args["latitude"])
    lon = replace_tenths(lon, args["longitude"])

if args["simple"]:
    print(str(lat) + "\n" + str(lon))
    sys.exit(0)

# Fancy output
print_fancy_output(lat, lon, args["browser"])
check_find_nearby(lat, lon, args)

if args["open_og_comic"]:
    webbrowser.open("https://xkcd.com/426/")
if args["open_geohashing_home"]:
    webbrowser.open("https://geohashing.site/")
