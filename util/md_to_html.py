#!/usr/bin/env python3

import argparse
import jinja2
import markdown
import sys


def main(args=None):
    d = 'Render an HTML document from a Markdown file and a Jinja2 template.'
    parser = argparse.ArgumentParser(description=d)
    parser.add_argument('mdfile', type=argparse.FileType('r'), nargs='?',
                        help='File to convert. Defaults to stdin.')
    parser.add_argument('-o', '--out', type=str,
                        help='Output file name. Defaults to stdout.')
    parser.add_argument('-t', '--template', type=str,
                        help='File containing Jinja2 template to use.')
    args = parser.parse_args(args)

    # Input files
    md = args.mdfile.read()
    with open(args.template, 'r') as f:
        template = f.read()

    # Parse markdown
    extensions = ['extra', 'smarty']
    html = markdown.markdown(md, extensions=extensions, output_format='html5')

    # Render HTML
    doc = jinja2.Template(template).render(content=html)
    with open(args.out, 'w+') as f:
        f.write(doc)


if __name__ == '__main__':
    sys.exit(main())
