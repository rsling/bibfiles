import sys
import re
from unidecode import unidecode
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
import requests
import urllib
import time

# Search for the DOI given a title; e.g.  "computation in Noisy Radio Networks"
# Credit to user13348, slight modifications
# http://tex.stackexchange.com/questions/6810/automatically-adding-doi-fields-to-a-hand-made-bibliography
#


class DOIError(Exception):
    pass


def searchdoi(title, author, tries=4):
    params = urllib.parse.urlencode(
        {"query.author": author, "query.title": title})
    url_base = "http://api.crossref.org/works?"
    trying = True
    try_count = 0
    while trying and try_count <= tries:
        response = requests.get(url_base + params)
        if response.ok:
            trying = False
            try:
                doi = response.json()['message']['items'][0]['DOI']
            except:
                print("something wrong with json response for " + params)
                raise DOIError
        else:
            try_count += 1
            print("Response not 200 OK. Retrying, try " + str(try_count)
                + " of " + str(tries))
            time.sleep(1)
    if try_count >= tries:
        raise DOIError("Tried more than " + str(tries) + " times. Response"
                    " still not 200 OK! Uh oh...")
    return doi
#print(response.status, response.reason)


def normalize(string):
    """Normalize strings to ascii, without latex."""
    string = re.sub(r'[{}\\\'"^]', "", string)
    # better remove all math expressions
    string = re.sub(r"\$.*?\$", "", string)
    return unidecode(string)


def get_authors(entry):
    """Get a list of authors' or editors' last names."""
    def get_last_name(authors):
        for author in authors:
            author = author.strip(" ")
            if "," in author:
                yield author.split(",")[0]
            elif " " in author:
                yield author.split(" ")[-1]
            else:
                yield author

    try:
        authors = entry["author"]
    except KeyError:
        authors = entry["editor"]

    authors = normalize(authors).split("and")
    return list(get_last_name(authors))


def main(bibtex_filename):
    print("Reading Bibliography...")
    with open(bibtex_filename) as bibtex_file:
        bibliography = bibtexparser.load(bibtex_file)

    print("Looking for Dois...")
    before = 0
    new = 0
    total = len(bibliography.entries)
    for i, entry in enumerate(bibliography.entries):
        print("\r{i}/{total} entries processed, please wait...".format(i=i,
                                                                    total=total), flush=True, end="")
        try:
            if "doi" not in entry or entry["doi"].isspace():
                title = entry["title"]
                authors = entry["author"]
                try:
                    doi = searchdoi(title, authors)
                    entry["doi"] = doi
                    new += 1
                except DOIError:
                    print("unable to find DOI for " + title)
            else:
                before += 1
        except KeyError:
            print("some issue with this entry! No title or no author")
    print("")

    template = "We added {new} DOIs !\nBefore: {before}/{total} entries had DOI\nNow: {after}/{total} entries have DOI"

    print(
        template.format(
            new=new,
            before=before,
            after=before+new,
        total=total))
    outfile = bibtex_filename + "_doi.bib"
    print("Writing result to ", outfile)
    writer = BibTexWriter()
    writer.indent = '    '     # indent entries with 4 spaces instead of one
    with open(outfile, 'w') as bibfile:
        bibfile.write(writer.write(bibliography))

if __name__ == '__main__':
    main(sys.argv[1])
 
