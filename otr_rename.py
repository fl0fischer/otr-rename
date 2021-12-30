from os import listdir, rename
from os.path import isfile, isdir, join, split
import re
import difflib

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

import argparse

parser = argparse.ArgumentParser(description='Provide some command line options.')
parser.add_argument('dirpath', metavar='dirpath', type=str,
                    help='absolute directory path of files to rename')

parser.add_argument('-n', dest='dry_run', action='store_const',
                    const=True, default=False,
                    help='whether to perform a dry run (default: False)')
parser.add_argument('--series', metavar='series_name', type=str, default=None,
                    help='name of series')
parser.add_argument('--method', metavar='title_update_method', type=str, default=None,
                    help='method for updating movie titles using the IMDB database (None, "imdb_global", "imdb_closest", or "imdb_local") '
                         'WARNING: none of these methods is fully reliable ("imdb_local" might be best, though)!')

class otr_parser(object):
    """
    Object class that parses OTR file names, retrieves additional information, and renames files accordingly.
    :param series_name: name of series (str; None if otr_filenames correspond to movies)
    :param title_update_method: method for updating movie titles using the IMDB database (str; None if original name should be used)
    :param dry_run: whether to perform a dry run (bool)
    """
    def __init__(self,  series_name=None, title_update_method=None, dry_run=True):

        self.otr_filename_regex = r"([a-zA-Z0-9_.-]*)_([0-9]{2}.[0-9]{2}.[0-9]{2})_([0-9]{2}-[0-9]{2})_([a-zA-Z0-9]*)_([0-9]*)_TVOON_DE.mpg.(HD|HQ)?.?(avi|mp4)"

        # Umlaut mapping
        self.umap = {'Ae': "Ä", u'Oe': "Ö", u'Ue': "Ü", u'ae': "ä", u'oe': "ö", u'ue': "ü"}

        self.title_update_method = title_update_method
        if self.title_update_method:
            import imdb
            self.ia = imdb.IMDb()

        self.dry_run = dry_run

        # Get list of channel names
        self.channels_URL = "https://www.fernsehserien.de/serien-nach-sendern"
        page_channels = requests.get(self.channels_URL, allow_redirects=True)
        assert page_channels.status_code == 200, f"Cannot read channel names from page '{self.channels_URL}'."
        soup_channels = BeautifulSoup(page_channels.content, "html.parser")
        self.fernsehserien_de_channels = [channel.attrs["value"] for channel in soup_channels.select("div.serien-nach-sendern-auswahl")[0].find_all(attrs={"id" : "select-sender"})[0].find_all("option")]
        self.custom_channel_dict = {'ard': 'das-erste', 'swr': 'swr-fernsehen', 'hr': 'hr-fernsehen', 'srtl': 'superrtl', 'orf3': 'orf-iii'}  #custom channel name mappings
        for channel_name in self.custom_channel_dict.values():
            assert channel_name in self.fernsehserien_de_channels, f"Channel name '{channel_name}' in channel_dict does not match channel name used by fernsehserien.de!"

        self.series_name = series_name

        if self.series_name:
            self.series_name_ID = "-".join(self.series_name.split())
            self.main_URL = f"https://www.fernsehserien.de/{self.series_name_ID}/"

            page = requests.get(self.main_URL, allow_redirects=True)
            assert page.status_code == 200, f"Cannot find page '{self.main_URL}'.\nTry a series name different than '{self.series_name}'."


    def __getattr__(self, channelname):
        if self.series_name:
            newattr = otr_series_channel(channelname, self.main_URL)
            setattr(self, channelname, newattr)
            return newattr


    def rename(self, path):
        """
        Renames filename.
        :param path: path of file (or directory of files) to rename
        :return: None
        """

        if isdir(path):
            dirpath = path
            otr_filenames = [f for f in listdir(dirpath) if isfile(join(dirpath, f)) if
                             ("TVOON" in f) and (f.endswith(".avi") or f.endswith(".mp4"))]
        elif isfile(path):
            dirpath, filename = split(path)
            assert "TVOON" in filename, "Invalid filename."
            otr_filenames = [filename]
        else:
            raise TypeError("Invalid path (should be file or directory path).")

        otr_filenames_vars = [(" ".join(
            (filename_vars := re.findall(self.otr_filename_regex, filename)[0])[0].replace("__", " - ").split("_")),
                               *filename_vars[1:], filename) for filename in otr_filenames if
            "TVOON" in filename]  # exclude filenames that were already adjusted

        if self.series_name:  # TV series -> get episode names and IDs from fernsehserien.de
            for name, date, time, channel, duration, *fileformat, filename in otr_filenames_vars:
                fileformat_substring = f" [{fileformat[0]}]" if fileformat[0] != "" else ""

                airdate = datetime.strptime('/'.join([date, time]), '%y.%m.%d/%H-%M')

                current_channelname = self.custom_channel_dict.get(channel,
                                                              difflib.get_close_matches(channel, self.fernsehserien_de_channels,
                                                                                        n=1, cutoff=0.1)[0])

                if matches := getattr(self, current_channelname).find_airdate(airdate):
                    ep_title = matches[0].select('span.sendetermine-2019-episodentitel')[0].find(text=True,
                                                                                                 recursive=False).strip()
                    season_id, season_ep_id = matches[0].select('span.sendetermine-2019-staffel-und-episode-smartphone')[
                        0].text.split('.')

                    new_filename = f"{self.series_name} {season_id}.{season_ep_id}{fileformat_substring} ({ep_title}).avi"  #DEFINE FILENAME FORMAT
                    new_filename = new_filename.replace(':', ' -').translate(
                        str.maketrans('', '', """<>:"/\|?*"""))  # remove invalid characters from filename (Windows)
                    print(f"RENAME{' (dry-run)' if self.dry_run else ''}: {join(dirpath, filename)} -> {join(dirpath, new_filename)}")
                    if not self.dry_run:
                        rename(join(dirpath, filename), join(dirpath, new_filename))

        else:  # movie -> only make filename more readable
            for name, date, time, channel, duration, *fileformat, filename in otr_filenames_vars:
                new_name = name
                if self.title_update_method:
                    imdb_search = [i for i in self.ia.search_movie(name) if i.get("kind") in ["movie", "tv movie"]]
                    # imdb_search = [i for i in self.ia.search_movie(name, results=5) if self.ia.get_movie(i.movieID).get("kind") in ["movie", "tv movie"]]  #takes too long
                    if (len(imdb_search) == 0):  #try it again with umlauts
                        for k, v in self.umap.items():
                            name = name.replace(k, v)
                        imdb_search = [i for i in self.ia.search_movie(name) if i.get("kind") in ["movie", "tv movie"]]
                    if len(imdb_search) >= 1:
                        if self.title_update_method == "imdb_global":
                            ## Variant 1 - use global imdb name
                            suggested_names = [imdb_search[0]["title"]]
                        elif self.title_update_method == "imdb_closest":
                            ## Variant 2 - use closest (global) imdb name (including alternative names)
                            imdb_names = [title for imdb_result in imdb_search for title in (
                                [imdb_result["title"]] + imdb_result.data['akas'] if 'akas' in imdb_result.data else [
                                    imdb_result["title"]])]
                            suggested_names = difflib.get_close_matches(name, imdb_names, n=1, cutoff=0.1)
                        elif self.title_update_method == "imdb_local":
                            ## Variant 3 - use local imdb name
                            suggested_names = [
                                re.split(" \([0-9]{4}\)", self.ia.get_movie(imdb_search[0].movieID).get("localized title"))[
                                    0]]  # removes year at the end of the localized title
                        else:
                            raise NotImplementedError
                        if len(suggested_names) >= 1:
                            new_name = suggested_names[0]

                fileformat_substring = f" [{fileformat[0]}]" if fileformat[0] != "" else ""
                new_filename = f"{new_name}{fileformat_substring}.avi"  #DEFINE FILENAME FORMAT
                new_filename = new_filename.replace(':', ' -').translate(
                    str.maketrans('', '', """<>:"/\|?*"""))  # remove invalid characters from filename (Windows)
                print(f"RENAME{' (dry-run)' if self.dry_run else ''}: {join(dirpath, filename)} -> {join(dirpath, new_filename)}")
                # print(f"RENAME{' (dry-run)' if self.dry_run else ''}: {name} -> {join(dirpath, new_filename)}")
                if not self.dry_run:
                    rename(join(dirpath, filename), join(dirpath, new_filename))

class otr_series_channel(dict):
    """
    Dictionary that includes parsed fernsehserien.de subpages of air dates for a given tv series and channel.
    Non-existing values are computed on the fly.
    :param channelname: channel name (str)
    :param main_URL: URL of format "https://www.fernsehserien.de/<series_name>/" (str)
    """

    def __init__(self, channelname, main_URL):
        super(otr_series_channel, self).__init__()
        self.channelname = channelname
        self.channel_URL = join(main_URL, f"sendetermine/{channelname}/")

        self.series_name = main_URL.split("/")[-2] if main_URL.endswith("/") else main_URL.split("/")[-1]

        self.page_counter = -1

    def __getitem__(self, key):
        try:
            val = super(otr_series_channel, self).__getitem__(key)
            return val
        except KeyError:
            if isinstance(key, int):
                URL = join(self.channel_URL, f"{key}")
                page = requests.get(URL, allow_redirects=True)
                assert page.status_code == 200, f"Cannot find page '{URL}'."
                assert page.url.endswith(str(key)), f"Cannot read page '{URL}' without redirecting to other subpage."
                soup = BeautifulSoup(page.content, "html.parser")

                super(otr_series_channel, self).__setitem__(key, soup)  # avoid re-computation of this attribute
                return soup

    def get(self, key, default=None):
        return self.__getitem__(key) or super(otr_series_channel, self).get(key, default)


    def find_airdate(self, airdate):
        """
        Finds entry in fernsehserien.de database that matches desired air date, tv series, and channel.
        :param airdate: desired air date (datetime)
        :return: list of matching entries, only if air date exists (or closest air date was accepted by user)
        """

        while True:
            try:
                soup = self.get(self.page_counter)
            except AssertionError as e:
                print(f"Cannot find entry for '{self.series_name}' at {airdate} at '{self.channelname}'.")
                return
            # check if date range of current page covers desired date
            # currentpage_daterange = [min(daterange := [datetime.strptime(currentdate, '%d.%m.%Y') for currentdate in soup()[0].select('h2.episode-ueberschrift')[0].text.split('–')]), max(daterange) + timedelta(days=1)]  #add one day to date range since hours and minutes are missing here (inaccurate date range)
            currentpage_daterange = [min(alldates := [
                datetime.strptime(j.select('span.sendetermine-2019-wochentag')[0].text.split("–")[0].split()[1],
                                  "%d.%m.%Y%H:%M") for i in
                soup.select('div.sendetermine-2019.sendetermine-2019-sendung') for j in i.select('a')]),
                                     max(alldates)]

            if airdate < currentpage_daterange[0]:
                self.page_counter -= 1
            elif airdate > currentpage_daterange[1]:
                self.page_counter += 1
            else:
                break

        matches = [j for i in soup.select('div.sendetermine-2019.sendetermine-2019-sendung') for j in i.select('a')
                   if (airdate == datetime.strptime(
                j.select('span.sendetermine-2019-wochentag')[0].text.split("–")[0].split()[1], "%d.%m.%Y%H:%M"))]
        if len(matches) != 1:
            closest_airdate = min(alldates, key=lambda d: abs(d - airdate))
            yesno = input(
                f"Cannot find database entry for desired air date '{airdate}'.\nShould use '{closest_airdate}' instead (y/n)? ")
            if yesno.lower() in ["y", "j", "yes", "ja"]:
                airdate = closest_airdate
                matches = [j for i in soup.select('div.sendetermine-2019.sendetermine-2019-sendung') for j in
                           i.select('a') if (airdate == datetime.strptime(
                        j.select('span.sendetermine-2019-wochentag')[0].text.split("–")[0].split()[1],
                        "%d.%m.%Y%H:%M"))]
                assert len(matches) == 1
            else:
                return
        return matches


if __name__=="__main__":

    args = parser.parse_args()

    otr = otr_parser(series_name=args.series, title_update_method=args.method, dry_run=args.dry_run)

    # Create list of filenames to modify (exclude filenames that were already adjusted)
    otr_filenames = [join(args.dirpath, f) for f in listdir(args.dirpath) if isfile(join(args.dirpath, f)) if (f.endswith(".avi") or f.endswith(".mp4"))]

    for otr_filename in otr_filenames:
        otr.rename(otr_filename)