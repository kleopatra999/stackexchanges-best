import requests, csv, sys, argparse, re, textwrap
from pprint import pprint

def main():
    args        = parse_args()
    out         = sys.stdout
    page        = args.pages.start
    try:
        while True:
            results = best(args, page)
            write_results(out, args, results)
            if not results['has_more']:
                break
            if page == args.pages.stop:
                break
            page = page + 1
    except requests.exceptions.HTTPError as e:
        try:
            content = e.response.json()['error_message']
        except:
            content = e.response.text
        msg = ('{}\n'\
            +'The request for {} failed.\n'\
            +'Response says {}.')\
            .format(e, e.request.url, content)
        print(msg, file = sys.stderr)

def parse_args():
    class HelpFormatter(argparse.RawDescriptionHelpFormatter):
        def add_argument(self, action):
            add_argument = super(HelpFormatter, self).add_argument
            if action.dest == "help":
                return add_argument(action)
            if action.default and action.help:
                action.help = action.help + ' (default "%(default)s")'
            if action.default and not action.help:
                action.help = 'default "%(default)s"'
            return add_argument(action)
    epilog_pages = """
        PAGES  is  START[-][STOP]  for start and stop pages.
        If only START is given,
          read only this page.
          Pages at Stack Exchange start at 1.
        If - is given and STOP is omitted,
          it reads every page beginning with START
          until there is no page left.
        If - and STOP are given
          it reads from START to STOP and not beyond.
        PAGES must match /{pages_regex}/."""\
            .format(pages_regex = Pages.regex)
    epilog_csv_fields = """
        CSV_FIELDS is a comma separated list of fields
          which get written as CSV output.
        Possible values are specified in
          https://api.stackexchange.com/docs/types/question .
        If it contains the field "all",
          every field will be written."""
    epilog = "\n\n".join(
        textwrap.fill(" ".join(x.split())) for x in 
        [epilog_pages, epilog_csv_fields])
    p = argparse.ArgumentParser(
        formatter_class = HelpFormatter,
        epilog          = epilog)
    p.add_argument("--site",
        default = "stackoverflow",
        help    = 'a Stack Exchange site')
    p.add_argument("--min",
        default = "1000")
    p.add_argument("--sort",
        default = "votes",
        choices = "activity creation votes relevance".split())
    p.add_argument("--order",
        default = "desc",
        choices = "desc asc".split())
    p.add_argument("--intitle",
        default = "a")
    p.add_argument("--pages",
        default = "1-",
        type    = Pages,
        help    = "PAGES gives the pages to download")
    p.add_argument("--print-request-urls",
        action  = 'store_true')
    p.add_argument("--csv-fields",
        default = "score,title,link",
        type    = lambda x: x.split(","),
        help    = "which fields of the question should be written")
    p.add_argument("--csv-dialect",
        default = "unix",
        choices = "excel excel-tab unix".split())
    return p.parse_args()

class Pages:
    regex = "^([1-9]\d*)(?:(-)([1-9]\d*)?)?$"
    def __init__(self, string):
        m = re.match(self.regex, string)
        if not m:
            raise argparse.ArgumentTypeError(
                'PAGES needs to be START[-][STOP] ("{}") but is "{}".'.\
                format(self.regex, string))
        start, dash, stop = m.groups()
        self.start  = int(start)
        if dash:
            self.stop = stop and int(stop) or "dont stop"
        else:
            self.stop = self.start


def best(args, page):
    # https://api.stackexchange.com/docs/search
    version     = "2.2"
    route       = "search"
    query       = dict(
        intitle     = args.intitle,
        site        = args.site,
        sort        = args.sort,
        order       = args.order,
        min         = args.min,
        page        = page)
    url         = "https://api.stackexchange.com/{}/{}".\
        format(version, route)
    response    = requests.get(url, query)
    if args.print_request_urls:
        print("request: " + response.request.url, file = sys.stderr)
    response.raise_for_status()
    return response.json()

def write_results(out, args, results):
    if "all" in args.csv_fields:
        args.csv_fields = list(results['items'].keys())
    # https://docs.python.org/3/library/csv.html#csv.DictWriter
    # 'extrasaction' is no typo here
    w = csv.DictWriter(out, args.csv_fields,
        extrasaction    = "ignore",
        dialect         = args.csv_dialect)
    for result in results['items']:
        w.writerow(result)

if __name__ == '__main__':
    main()
