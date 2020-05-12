from argparse import ArgumentParser, FileType


def get_base_ns(namespace, context):
    #print(context)

    ## if the context comes in as a string, break it into a list
    if type("") == type(context):
        context = context.split("\n")
        
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
    parser.add_argument('context', type=FileType('r'), help='Context file')
    parser.add_argument('namespace', type=str, help='Ontology namespace')
    args = parser.parse_args()
    print(get_base_ns(args.namespace, args.context))
