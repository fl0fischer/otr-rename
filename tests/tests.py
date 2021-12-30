from otr_rename import otr_parser
from pathlib import Path

def test_movies(title_update_method=None):

    otr = otr_parser(title_update_method=title_update_method, dry_run=True)

    filename_list = ["James_Bond_007_Lizenz_zum_Toeten_21.12.26_22-50_sf2_135_TVOON_DE.mpg.HD.avi",
                     "Drachenzaehmen_leicht_gemacht_3__Die_geheime_Welt_21.12.26_14-10_orf1_90_TVOON_DE.mpg.HD.avi"]

    for filename in filename_list:   #create test files
        Path(filename).touch()

    for otr_filename in filename_list:
        otr.rename(otr_filename)

    for filename in filename_list:   #delete test files
        Path(filename).unlink()


def test_series():

    otr = otr_parser(series_name="Family Guy", dry_run=True)

    filename_list = ["Family_Guy_21.12.28_23-55_pro7maxx_20_TVOON_DE.mpg.mp4",
                     "Family_Guy_S12E19_16.02.23_21-40_pro7_30_TVOON_DE.mpg.HQ.avi",
                     "Bobs_Burgers_21.12.27_08-05_comedycentral_30_TVOON_DE.mpg.mp4"]

    for filename in filename_list:   #create test files
        Path(filename).touch()

    for otr_filename in filename_list:
        otr.rename(otr_filename)

    for filename in filename_list:   #delete test files
        Path(filename).unlink()


if __name__=="__main__":

    test_movies()
    test_movies(title_update_method="imdb_closest")
    test_movies(title_update_method="imdb_local")
    test_series()