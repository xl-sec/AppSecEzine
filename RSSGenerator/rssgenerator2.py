import re
import sys
import git
import datetime

from feedgen.feed import FeedGenerator

class EzineItem:
    def __init__(self):
        self.title = ''
        self.category = ''
        self.url = ''
        self.urls = []
        self.content = []
        self.content_raw = ''

    def __str__(self):
        return f"EzineItem(title={self.title}, category={self.category}, url={self.url}, urls={self.urls})"

class Ezine:
    def __init__(self):
        self.edition = 0
        self.date = datetime.datetime.now()
        self.credits = ''
        self.url = ''
        self.raw = ''
        self.items = []

    def title(self):
        return 'AppSec Ezine #' + self.edition

    def __str__(self):
        return f"Ezine(\n  edition={self.edition},\n  date={self.date},\n  credits={self.credits},\n  url={self.url},\n  items={self.items}\n)"

output_dir = "output/"
base_url = "https://xl-sec.github.io/AppSecEzine/"

categories = {
    'mustsee': "Must see",
    'hack': "Hack",
    'security': "Security",
    'fun': "Fun",
    'credits': "Credits"
}

d2c = {
    "Something that really worth your time!": 'mustsee',
    "Something that's really worth your time!": 'mustsee',
    "Some Kung Fu Techniques.": 'hack',
    "Some Kung Fu Techniques/Tools.": 'hack',
    "All about security issues.": 'security',
    "All about security issues/problems.": 'security',
    "Spare time?": 'fun',
    "Spare time ?": 'fun',
    "Content Helpers (0x)": 'credits',
}

def parse_ezine(path):
    result = Ezine()
    current_category = None
    current_item = EzineItem()
    extra_url_regexp = re.compile("([\w \-]+): (https?://[\w\./?&]+) ?")

    repo = git.Repo(".")
    date = next(repo.iter_commits(paths=path, max_count=1)).committed_datetime
    result.date = date

    with open(path, 'r') as fp:
        for row in fp:
            result.raw += row
            row = row.strip()
            if row == "":
                if current_item.title != "":
                    current_item.category = current_category
                    result.items.append(current_item)
                current_item = EzineItem()
                continue
            elif row[0] == "#":
                headers = row.strip(" #º").split("|")
                edition = headers[4].strip().split(" ")[1].strip(" #º")
                result.edition = edition
                continue
            elif row[0] == "'":
                row = row.strip(" '")
                if ord(row[0]) > 127:
                    continue
                if row in d2c:
                    current_category = d2c[row]
                else:
                    print("Unknown category: " + row, file=sys.stderr)
                continue

            if current_category == "credits":
                if row.startswith("http"):
                    result.url = row
                else:
                    result.credits = bytes.fromhex(row).decode('ascii')
                continue

            current_item.content_raw += row + "<br>\n"
            if row.startswith("Description:"):
                current_item.title = row[13:]
                current_item.content.insert(0, row)
            elif row.startswith("URL:"):
                url = row[5:].strip()
                if url.endswith("(+)"):
                    url = url[:-4]
                    current_item.urls += ("bit.ly inspect", url + "+")
                    current_item.content.append("bit.ly inspect: <a href='" + url + "+'>" + url + "+</a>")
                current_item.url = url
                current_item.content.insert(0, "URL: <a href='" + url + "'>" + url + "</a>")
            else:
                res = extra_url_regexp.match(row)
                if res:
                    current_item.urls += (res.group(1), res.group(2))
                    current_item.content.append(res.group(1) + ": <a href='" + res.group(2) + "'>" + res.group(2) + "</a>")
                else:
                    if ord(row[0]) > 127:
                        continue
                    print("EXTRA DATA FOUND", row)
                    current_item.content.append(row)

    generate_feed_split(result, "rss")
    generate_feed_split(result, "atom")
    generate_feed_whole(result, "rss")
    generate_feed_whole(result, "atom")

def generate_feed_split(ezine, mode):
    fg = FeedGenerator()
    fg.id(ezine.url)
    fg.title(ezine.title())
    fg.description(ezine.title())
    fg.pubDate(ezine.date)
    # todo: handle multiple credits
    fg.author({'name': ezine.credits,'email': "simpsonpt@gmail.com"})
    fg.link(href=ezine.url, rel='alternate')
    filename = "latest_split." + mode
    fg.link(href=base_url + filename, rel='self')
    fg.language('en')

    for item in ezine.items:
        fe = fg.add_entry(order='append')
        fe.title(categories[item.category] + ": " + item.title)
        fe.published(ezine.date)
        fe.content("<br>\n".join(item.content), type="html")
        fe.category({'term': categories[item.category]})
        fe.id(item.url)
        fe.link(href=item.url)

    with open(output_dir + filename, "w") as fp:
        if mode == "rss":
            fp.write(fg.rss_str(pretty=True).decode())
        else:
            fp.write(fg.atom_str(pretty=True).decode())

def generate_feed_whole(ezine, mode):
    fg = FeedGenerator()
    fg.id(ezine.url)
    fg.title(ezine.title())
    fg.description(ezine.title())
    fg.pubDate(ezine.date)
    # todo: handle multiple credits
    fg.author({'name': ezine.credits,'email': "simpsonpt@gmail.com"})
    fg.link(href=ezine.url, rel='alternate')
    filename = "latest_whole." + mode
    fg.link(href=base_url + filename, rel='self')
    fg.language('en')

    fe = fg.add_entry()
    fe.title(ezine.title())
    fe.published(ezine.date)
    # fe.content(ezine.raw.replace("  ", "&nbsp;&nbsp;").replace("\n", "<br>\n"), type="html")
    fe.content(ezine.raw, type="CDATA")
    fe.id(ezine.url)
    fe.link(href=ezine.url)

    with open(output_dir + filename, "w") as fp:
        if mode == "rss":
            fp.write(fg.rss_str(pretty=True).decode())
        else:
            fp.write(fg.atom_str(pretty=True).decode())

def main():
    if len(sys.argv) < 1 or len(sys.argv) > 2:
        print("Error: expecting path to ezine as argument", file=sys.stderr)
        print("rssgenerator2.py <path>", file=sys.stderr)
        sys.exit(1)

    parse_ezine(sys.argv[1])

if __name__ == "__main__":
    main()