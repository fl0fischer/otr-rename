# OTR Rename
<h2> OnlineTVRecorder - File Renaming Tool </h2>

<large>**This python script allows to easily rename movies and tv series episodes obtained from [OnlineTVRecorder](https://onlinetvrecorder.com/) in batch mode.**</large>

**Usage:**
- Movies:
  - `python otr_rename.py "C:\Path\to\file\directory"` 
  - `python otr_rename.py --method imdb_local "C:\Path\to\file\directory"` (get official (local) movie name from [IMDB](https://imdb.com/))
  - `python otr_rename.py --method imdb_closest "C:\Path\to\file\directory"` or `python otr_rename.py --method imdb_global "C:\Path\to\file\directory"` (get official (global) movie name from [IMDB](https://imdb.com/))
- Series:
  - `python otr_rename.py --series "some TV series title" "C:\Path\to\directory\with\episodes"` → sets episode title and season/episode ID for each filename by querying the [fernsehserien.de](https://www.fernsehserien.de/) database
- Other commands:
  - help: `python otr_rename.py -h`
  - dry-run (no renaming): `python otr_rename.py -n ...`

The filename format can be modified in `otr_rename.py` (search for `#DEFINE FILENAME FORMAT` comment).

**Requirements:**
- python>=3.9
- [requests](https://pypi.org/project/requests/)
- [beautifulsoup4](https://github.com/waylan/beautifulsoup)
- [IMDbPY](https://github.com/alberanid/imdbpy) (only if `--method` is used)

**Installation:**
`pip install -e .`
