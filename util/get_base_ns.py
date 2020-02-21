from argparse import ArgumentParser, FileType


def main(namespace, context):
    for line in context:
        if '{' in line or '}' in line:
            continue
        clean = line.strip().replace('"', '').replace(',', '')
        split = clean.split(':')
        ns = split.pop(0).strip()
        if ns.lower() == namespace.lower():
            return ns
    return ''


if __name__ == '__main__':
    parser = ArgumentParser(description='Retrieve base namespace')
    parser.add_argument('namespace', type=str, help='Ontology namespace')
    parser.add_argument('context', type=FileType('r'), help='Context file')
    args = parser.parse_args()
    print(main(args.namespace, args.context))
