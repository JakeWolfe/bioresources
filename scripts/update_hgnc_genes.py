import os
import re
import csv
import requests


def download_hgnc_entries():
    # Select relevant columns and parameters
    cols = ['gd_hgnc_id', 'gd_app_sym', 'gd_app_name', 'gd_status',
            'gd_aliases', 'gd_prev_sym', 'md_prot_id']
    statuses = ['Approved']
    params = {
        'hgnc_dbtag': 'on',
        'order_by': 'gd_app_sym_sort',
        'format': 'text',
        'submit': 'submit'
    }

    # Construct a download URL from the above parameters
    url = 'https://www.genenames.org/cgi-bin/download/custom?'
    url += '&'.join(['col=%s' % c for c in cols]) + '&'
    url += '&'.join(['status=%s' % s for s in statuses]) + '&'
    url += '&'.join(['%s=%s' % (k, v) for k, v in params.items()])

    # Save the download into a file
    res = requests.get(url)
    with open('hgnc_entries.tsv', 'wb') as fh:
        fh.write(res.content)


def generate_hgnc_terms():
    species = 'Human'
    entries = []
    nskipped = 0
    with open('hgnc_entries.tsv', 'r') as fh:
        reader = csv.reader(fh, delimiter='\t')
        next(reader)
        for row in reader:
            hgnc_id, hgnc_symbol, protein_name, status, synonyms_str, \
                prev_symbols_str, uniprot_ids_str = row
            uniprot_ids = [s.strip() for s in uniprot_ids_str.split(', ')] \
                if uniprot_ids_str else []
            # Skip genes that don't correspond to a single protein
            if len(uniprot_ids) != 1:
                nskipped += 1
                continue
            uniprot_id = uniprot_ids[0]
            synonym_list = [s.strip() for s in synonyms_str.split(', ')] \
                if synonyms_str else []
            prev_symbols_list = [s.strip()
                                 for s in prev_symbols_str.split(', ')] \
                if prev_symbols_str else []
            synonyms = [hgnc_symbol, protein_name] + synonym_list + \
                prev_symbols_list
            for synonym in synonyms:
                entries.append((synonym, uniprot_id, species))
    print('Found a total of %d entries and skipped %d rows' %
          (len(entries), nskipped))
    return entries


def remove_uniprot_redundancies(uniprot_file, hgnc_entries):
    print('Filtering %d entries from HGNC' % len(hgnc_entries))
    with open(uniprot_file, 'r') as fh:
        uniprot_entries = {(row[0], row[1])
                           for row in csv.reader(fh, delimiter='\t')
                           if row[2] == 'Human'}
    unique_hgnc_entries = [entry for entry in hgnc_entries
                           if (entry[0], entry[1]) not in uniprot_entries]
    print('Filtered to %d entries that aren\'t in UniProt' %
          len(unique_hgnc_entries))
    return unique_hgnc_entries


if __name__ == '__main__':
    # Basic positioning of folders
    here = os.path.dirname(os.path.abspath(__file__))
    kb_dir = os.path.join(here, os.pardir, 'src', 'main', 'resources', 'org',
                          'clulab', 'reach', 'kb')
    resource_fname = os.path.join(kb_dir, 'hgnc.tsv')
    #download_hgnc_entries()
    entries = generate_hgnc_terms()
    # We sort the entries first by the synonym but in a way that special
    # characters and capitalization is ignored, then sort by ID and then
    # by organism.
    entries = remove_uniprot_redundancies(os.path.join(kb_dir,
                                                       'uniprot-proteins.tsv'),
                                          entries)
    processed_entries = sorted(entries,
                               key=lambda x: (re.sub('[^A-Za-z0-9]', '',
                                                     x[0]).lower(), x[1],
                                              x[2]))
    # Now dump the entries into an updated TSV file
    with open(resource_fname, 'w') as fh:
        writer = csv.writer(fh, delimiter='\t')
        for entry in processed_entries:
            writer.writerow(entry)
